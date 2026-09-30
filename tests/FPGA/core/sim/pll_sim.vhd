library IEEE;
use IEEE.std_logic_1164.all;

-- Behavioral stand-in for the PLL of src/PLL/pll.vhd, for simulating
-- the hardware top (quartus/core_fpga_test.vhd) under GHDL.
--
-- src/PLL/pll.vhd wraps pll_0002.v, an altera_pll whose simulation model
-- is SystemVerilog, which GHDL does not run. This entity has the same
-- name and ports, so a simulation compiles it instead of src/PLL/pll.vhd
-- and the top needs no change. It is not part of the Quartus project
-- (quartus/ does not list it), so synthesis still uses the real PLL.
--
-- The parameters are the ones pll_0002.v sets: three outputs at the
-- reference frequency (50 MHz), 50 % duty cycle, phase shifted 0 ps,
-- 6667 ps and 13333 ps against the reference. Keep them in step with
-- pll_0002.v if the PLL changes.
--
-- locked: low while rst is high, and high LOCK_CYCLES reference clocks
-- after rst goes low, as a stand-in for the real lock time.
entity pll is
	port (
		refclk   : in  std_logic := '0';
		rst      : in  std_logic := '0';
		outclk_0 : out std_logic;
		outclk_1 : out std_logic;
		outclk_2 : out std_logic;
		locked   : out std_logic
	);
end entity pll;

architecture sim of pll is
	constant LOCK_CYCLES : natural := 10;
	signal c0, c1, c2 : std_logic := '0';
	signal lock_reg   : std_logic := '0';
begin
	c0 <= refclk;
	c1 <= transport refclk after 6667 ps;
	c2 <= transport refclk after 13333 ps;

	outclk_0 <= c0;
	outclk_1 <= c1;
	outclk_2 <= c2;

	process (refclk, rst)
		variable n : natural := 0;
	begin
		if rst = '1' then
			n := 0;
			lock_reg <= '0';
		elsif rising_edge(refclk) then
			if n < LOCK_CYCLES then
				n := n + 1;
			else
				lock_reg <= '1';
			end if;
		end if;
	end process;

	locked <= lock_reg;
end architecture sim;
