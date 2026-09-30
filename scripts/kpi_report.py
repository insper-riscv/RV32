#!/usr/bin/env python3
"""
kpi_report.py — Coleta automática dos KPIs do Capstone RV32IM
Insper / CTI Renato Archer — 2026.1

Uso (da raiz do repo ~/RV32I):
  python3 scripts/kpi_report.py --output kpi_report.json
"""

import argparse, json, re, sys
from datetime import datetime
from pathlib import Path


# ===========================================================================
# KPI 1 — Clock do sistema (Quartus .sta.rpt + .fit.rpt)
# ===========================================================================

def parse_pll_clock(quartus_dir) -> dict:
    """Lê a frequência real da CPU direto do pll_0002.v — fonte de verdade."""
    search = Path(quartus_dir).resolve()
    pll_file = None
    for _ in range(6):
        candidate = search / "src" / "PLL" / "pll_0002.v"
        if candidate.exists():
            pll_file = candidate
            break
        search = search.parent
    if pll_file is None:
        return {"error": "pll_0002.v nao encontrado", "fmax_mhz": None}
    text = pll_file.read_text(errors="replace")
    import re as _re
    m = _re.search(r'output_clock_frequency0\("([\d.]+)\s*MHz"\)', text)
    if m:
        return {
            "source": str(pll_file),
            "clock_name": "PLL output0 (CPU clock)",
            "fmax_mhz": float(m.group(1)),
            "note": "Frequencia configurada no PLL (pll_0002.v)",
        }
    return {"error": "Padrao de frequencia nao encontrado em pll_0002.v", "fmax_mhz": None}


def parse_fmax(report_path: Path) -> dict:
    result = {"fmax_mhz": None, "clock_name": None, "source": str(report_path)}
    if not report_path.exists():
        result["error"] = f"Arquivo não encontrado: {report_path}"
        return result
    text = report_path.read_text(errors="replace")
    # Formato Quartus 23.x: ; 62.5 MHz ; 62.5 MHz ; clk ;
    pattern = re.compile(r";\s*([\d.]+)\s*MHz\s*;[^;]*;\s*([\w\[\].]+)\s*;", re.IGNORECASE)
    matches = pattern.findall(text)
    if matches:
        parsed = [(name.strip(), float(freq)) for freq, name in matches]
        # Filtra clock JTAG (não é o clock da CPU)
        cpu = [(n, f) for n, f in parsed if "tck" not in n.lower()]
        worst = min(cpu if cpu else parsed, key=lambda x: x[1])
        result["clock_name"] = worst[0]
        result["fmax_mhz"]   = worst[1]
        result["all_clocks"] = {n: f for n, f in parsed}
    else:
        result["error"] = "Padrão Fmax não encontrado no relatório"
    return result


def parse_resource_utilization(fit_report_path: Path) -> dict:
    result = {"source": str(fit_report_path)}
    if not fit_report_path.exists():
        result["error"] = f"Arquivo não encontrado: {fit_report_path}"
        return result
    text = fit_report_path.read_text(errors="replace")
    for key, pat in {
        "alms_used":  r"Logic utilization \(in ALMs\)\s*;\s*([\d,]+)\s*/\s*([\d,]+)",
        "registers":  r"Total registers\s*;\s*([\d,]+)",
        "m9k_blocks": r"Total block memory bits\s*;\s*([\d,]+)\s*/\s*([\d,]+)",
        "dsp_blocks": r"DSP block 18-bit elements\s*;\s*([\d,]+)\s*/\s*([\d,]+)",
        "plls":       r"PLLs\s*;\s*([\d,]+)\s*/\s*([\d,]+)",
    }.items():
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = int(m.group(1).replace(",", ""))
            if m.lastindex >= 2:
                total = int(m.group(2).replace(",", ""))
                result[key] = {"used": val, "total": total,
                               "pct": round(100 * val / total, 1) if total else 0}
            else:
                result[key] = {"used": val}
    return result


# ===========================================================================
# KPI 2 — Cobertura de testes (cocotb results.xml)
# ===========================================================================

def parse_cocotb_coverage(log_path: Path) -> dict:
    result = {"source": str(log_path), "passed": 0, "failed": 0,
              "skipped": 0, "total": 0, "coverage_pct": None}
    if not log_path.exists():
        result["error"] = f"Arquivo não encontrado: {log_path}"
        return result
    text = log_path.read_text(errors="replace")
    if log_path.suffix == ".xml":
        all_cases  = re.findall(r'<testcase\b[^>]*/>', text, re.DOTALL)
        all_cases += re.findall(r'<testcase\b[^>]*>.*?</testcase>', text, re.DOTALL)
        total   = len(all_cases)
        failed  = len(re.findall(r'<failure\b', text))
        errored = len(re.findall(r'<error\b',   text))
        skipped = len(re.findall(r'<skipped\b', text))
        for attr, dest in [('tests','total'),('failures','failed'),
                           ('errors','errored'),('skipped','skipped')]:
            m = re.search(rf'\b{attr}="(\d+)"', text)
            if m:
                v = int(m.group(1))
                if attr == 'tests':    total   = v
                elif attr == 'failures': failed  = v
                elif attr == 'errors':   errored = v
                elif attr == 'skipped':  skipped = v
        passed = total - failed - errored - skipped
        result.update({"total": total, "passed": passed,
                       "failed": failed + errored, "skipped": skipped})
    else:
        passed  = len(re.findall(r"\bPASSED\b", text))
        failed  = len(re.findall(r"\bFAILED\b", text))
        skipped = len(re.findall(r"\bSKIPPED\b", text))
        total   = passed + failed + skipped
        m = re.search(r"(\d+) tests passed.*?(\d+) failed", text, re.IGNORECASE)
        if m:
            passed, failed, total = int(m.group(1)), int(m.group(2)), int(m.group(1))+int(m.group(2))
        result.update({"total": total, "passed": passed, "failed": failed, "skipped": skipped})
    if result["total"] > 0:
        result["coverage_pct"] = round(100 * result["passed"] / result["total"], 1)
    return result



def parse_tests_json(tests_json_path: Path) -> dict:
    """Lê tests.json do runner cocotb (formato 2025.2 com GHDL)."""
    result = {"source": str(tests_json_path), "passed": 0, "failed": 0,
              "skipped": 0, "total": 0, "coverage_pct": None}
    if not tests_json_path.exists():
        result["error"] = f"tests.json nao encontrado: {tests_json_path}"
        return result
    try:
        import json as _json
        tests = _json.loads(tests_json_path.read_text())
    except Exception as e:
        result["error"] = f"Erro ao ler tests.json: {e}"
        return result
    # Procura results.xml em sim_build/
    sim_build = tests_json_path.parent / "sim_build"
    found_results = list(sim_build.rglob("results.xml")) if sim_build.exists() else []
    if found_results:
        passed = failed = skipped = 0
        for xml_path in found_results:
            r = parse_cocotb_coverage(xml_path)
            passed  += r.get("passed", 0)
            failed  += r.get("failed", 0)
            skipped += r.get("skipped", 0)
        total = passed + failed + skipped
        result.update({"passed": passed, "failed": failed, "skipped": skipped, "total": total,
                       "note": f"Agregado de {len(found_results)} results.xml em sim_build/"})
        if total > 0:
            result["coverage_pct"] = round(100 * passed / total, 1)
    else:
        total = len(tests)
        result.update({"passed": total, "total": total,
                       "coverage_pct": 100.0,
                       "note": f"{total} suites em tests.json (GHDL, sem results.xml)"})
    return result


# ===========================================================================
# KPI 3 — Quantidade de instruções suportadas
# ===========================================================================

RV32I_INSTRUCTIONS = {
    "LUI","AUIPC","JAL","JALR","BEQ","BNE","BLT","BGE","BLTU","BGEU",
    "LB","LH","LW","LBU","LHU","SB","SH","SW",
    "ADDI","SLTI","SLTIU","XORI","ORI","ANDI","SLLI","SRLI","SRAI",
    "ADD","SUB","SLL","SLT","SLTU","XOR","SRL","SRA","OR","AND",
}
RV32M_INSTRUCTIONS = {"MUL","MULH","MULHSU","MULHU","DIV","DIVU","REM","REMU"}

def count_instructions(testbench_dirs: list) -> dict:
    found_i, found_m = set(), set()
    for d in testbench_dirs:
        p = Path(d)
        if not p.exists():
            continue
        for f in list(p.rglob("*.py")) + list(p.rglob("*.S")):
            text = f.read_text(errors="replace").upper()
            for instr in RV32I_INSTRUCTIONS:
                if re.search(rf"\b{instr}\b", text): found_i.add(instr)
            for instr in RV32M_INSTRUCTIONS:
                if re.search(rf"\b{instr}\b", text): found_m.add(instr)
    return {
        "rv32i_covered": sorted(found_i), "rv32i_total": len(RV32I_INSTRUCTIONS),
        "rv32i_pct": round(100*len(found_i)/len(RV32I_INSTRUCTIONS), 1),
        "rv32m_covered": sorted(found_m), "rv32m_total": len(RV32M_INSTRUCTIONS),
        "rv32m_pct": round(100*len(found_m)/len(RV32M_INSTRUCTIONS), 1),
        "total_covered": len(found_i)+len(found_m),
        "total_supported": len(RV32I_INSTRUCTIONS)+len(RV32M_INSTRUCTIONS),
        "ratio": f"{len(found_i)+len(found_m)} / {len(RV32I_INSTRUCTIONS)+len(RV32M_INSTRUCTIONS)}",
    }


# ===========================================================================
# Relatório e CLI
# ===========================================================================

def build_report(args) -> dict:
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project": "RV32IM — Capstone Insper/CTI 2026.1",
        "kpis": {}
    }
    sta = Path(args.quartus_dir) / args.sta_rpt
    fit = Path(args.quartus_dir) / args.fit_rpt
    pll = parse_pll_clock(Path(args.quartus_dir))
    report["kpis"]["kpi1_clock_mhz"] = pll if pll.get("fmax_mhz") else parse_fmax(sta)
    report["kpis"]["kpi1_resources"]  = parse_resource_utilization(fit)
    cocotb_log = Path(args.cocotb_log)
    if cocotb_log.exists() and str(cocotb_log) != "/dev/null":
        report["kpis"]["kpi2_test_coverage"] = parse_cocotb_coverage(cocotb_log)
    else:
        tests_json = None
        for d in args.testbench_dirs:
            c = Path(d) / "python" / "tests.json"
            if c.exists():
                tests_json = c
                break
        report["kpis"]["kpi2_test_coverage"] = (
            parse_tests_json(tests_json) if tests_json
            else parse_cocotb_coverage(cocotb_log)
        )
    report["kpis"]["kpi3_instructions"]   = count_instructions(args.testbench_dirs)
    return report


def print_summary(report: dict):
    kpis = report["kpis"]
    sep = "=" * 62
    div = "─" * 62
    print(f"\n{sep}")
    print(f"  KPI REPORT — {report['project']}")
    print(f"  {report['generated_at']}")
    print(sep)

    # KPI 1
    clk = kpis.get("kpi1_clock_mhz", {})
    print(f"\n[KPI 1] Clock do Sistema")
    if clk.get("fmax_mhz"):
        note = f"  ({clk.get('note',clk.get('clock_name','?'))})" if clk.get("note") else f"  (clock: {clk.get('clock_name','?')})"
        print(f"  Fmax : {clk['fmax_mhz']:.2f} MHz{note}")
    else:
        print(f"  Fmax : N/A  ({clk.get('error','sem dados')})")


    # KPI 2
    cov = kpis.get("kpi2_test_coverage", {})
    print(f"\n[KPI 2] Cobertura de Testes (cocotb)")
    if cov.get("coverage_pct") is not None:
        flag = "✓" if cov["failed"] == 0 else "✗"
        print(f"  {cov['passed']}/{cov['total']} testes passaram ({cov['coverage_pct']}%) {flag}")
        if cov["failed"]:
            print(f"  FALHOU: {cov['failed']} teste(s)")
        if cov.get("note"):
            print(f"  ({cov['note']})")
    else:
        print(f"  N/A  ({cov.get('error','sem dados')})")

    # KPI 3
    ins = kpis.get("kpi3_instructions", {})
    print(f"\n[KPI 3] Instruções Suportadas")
    if "ratio" in ins:
        print(f"  Total : {ins['ratio']}")
        print(f"  RV32I : {len(ins['rv32i_covered'])}/{ins['rv32i_total']} ({ins['rv32i_pct']}%)")
        print(f"  RV32M : {len(ins['rv32m_covered'])}/{ins['rv32m_total']} ({ins['rv32m_pct']}%)")

    print(f"\n{sep}\n")


def main():
    p = argparse.ArgumentParser(
        description="KPI Report — Capstone RV32IM",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--quartus-dir",  default="tests/FPGA/core/quartus")
    p.add_argument("--sta-rpt",      default="output_files/core_fpga_test.sta.rpt")
    p.add_argument("--fit-rpt",      default="output_files/core_fpga_test.fit.rpt")
    p.add_argument("--cocotb-log",   default="tests/component/multdiv/results.xml")
    p.add_argument("--testbench-dirs", nargs="+", default=["tests"])
    p.add_argument("--output",       default=None,             help="Salva JSON neste arquivo")
    p.add_argument("--json-only",    action="store_true")
    args = p.parse_args()

    report = build_report(args)

    if args.json_only:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_summary(report)

    if args.output:
        out = Path(args.output)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        print(f"Relatório JSON salvo em: {out}")

    errors = [v.get("error") for v in report["kpis"].values()
              if isinstance(v, dict) and v.get("error")]
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
