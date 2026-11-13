# TR10_cmp_sc PDN + CTS experiment

## Config

`examples/tr1um_fifo4_cmp/config.json`:

```json
"RUN_CTS": true,
"RUN_IRDROP_REPORT": true
```

Run tag `cts`, flow to `OpenROAD.CTS`, then guide generated from the CTS DEF
(`runs/cts/34-openroad-cts/tr1um_fifo4_cmp.def`) and DRT/STA/IR-drop resumed.

## CTS result

`runs/cts/34-openroad-cts/cts.rpt`:

```
Total number of Clock Roots: 1.
Total number of Buffers Inserted: 3.
Total number of Clock Subnets: 3.
Total number of Sinks: 23.
Cells used: BUF_X2: 3
Dummys used: INV_X1: 1
```

CTS log: path depth 2, average sink wire length 1740.38 um, clock buffer
area 2886.84 um^2, clock inverter area 641.52 um^2.

CTS/STA metrics (`runs/cts/final/metrics.json`):

| metric | value |
|---|---|
| clock skew worst setup | **2.014 ns** |
| clock skew worst hold | **-2.001 ns** |
| setup slack | 4967.26 ps |
| hold slack | +2.269 ns |
| instance area | 225,815 um^2 |
| utilization | 19.91 % |

Post-route STA (`runs/cts/45-openroad-stapostpnr/summary.rpt`) after CTS and
DRT:

| metric | value |
|---|---|
| setup worst slack | **4781.99 ps**, 0 setup violations |
| hold worst slack | **-14.97 ps**, **19 hold violations** |
| hold TNS | **-181.45 ps** |
| max cap / max slew violations | 75 / 160 |

The CTS clock tree improves setup margin but **introduces hold violations**
(the no-CTS baseline had hold WNS 0). `RUN_POST_CTS_RESIZER_TIMING` is still
false; a post-CTS hold repair/resizer pass is needed.

DRT with the CTS DEF and regenerated guide: **0 violations** (final).

## PDN / IR-drop result

The PDN was already enabled as `pdn_cmp_sc.tcl` followpins only:

* M1 followpin rails at the row boundaries, full width (x 10.8..745.2);
* no M2 straps, no ring, no top-level VDD/GND power terminals;
* GeneratePDN: `PSM-0025 VDD/GND does not contain any terminals`;
* `design__power_grid_violation__count = 2`.

The IR-drop step then fails:

```
analyze_power_grid -net VDD -voltage_file .../net-VDD.csv
[ERROR PSM-0069] Check connectivity failed on VDD.
```

Unconnected instances are the CTS clock buffers and TAP2 cells, e.g.:

```
_121_/VDD at (642.6, 1007.4)
TAP_TAPCELL_ROW_2_5/VDD at (665.55, 162.15)
_166_/VDD at (680.4, 532.2)
_189_/VDD at (702.0, 294.6)
```

Root cause: the manual placement rows (237.6 um), TAP2 insertion rows
(e.g. y=162.15), CTS DPL rows (e.g. y=294.6/532.2) and the followpin row grid
are not aligned; the CTS buffers are added after PDN and
`Odb.SetPowerConnections` is not re-run after CTS. The followpin-only PDN has
no M2 strap/ring to pick up the TAP2 M2 PG straps or reach the off-row CTS
buffers. **No valid IR-drop number was obtained.**

## Next required changes

1. Align TAP2 / CTS clock buffers to the used 237.6 um rows (or add followpin
   rails on every DPL row).
2. Add M2 vertical PDN stripes at the TAP2 columns
   (x ~ 229.5/234.9 + n*216), a power ring and top-level VDD/GND pins.
3. Re-run `set_power_connections` after CTS.
4. Re-run PDN/DRT/IR-drop.
5. Optionally enable/post-run CTS hold repair (the CTS tree currently gives
   19 hold violations, -14.97 ps).
