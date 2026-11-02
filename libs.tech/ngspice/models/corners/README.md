# TR10 Engineering Process Corners

These are **engineering** corner decks, not silicon-fitted sign-off corners.
The OS00-calibrated baseline carries no measured die-to-die spread, so the
offsets below are fixed engineering assumptions chosen to bracket plausible
variation. Use them for robustness screening only; never quote them as
foundry-guaranteed SS/FF/FS/SF data.

## Usage

A corner file is self-contained: it includes the baseline manifest and then
overrides the exposed `.param` hooks. In a netlist simply include the corner
instead of the baseline manifest:

```spice
* Typical (baseline)
*.include ".../models/ip62_models_calibrated"

* Slow-Slow engineering corner
.include ".../models/corners/eng_ss.spice"
```

Available corners: `eng_tt`, `eng_ss`, `eng_ff`, `eng_fs`, `eng_sf`.

## Hook semantics

| Hook        | Baseline | Meaning                                          |
|-------------|----------|--------------------------------------------------|
| `vthMP`     | 0        | PMOS threshold offset added to `vth0` (V).        |
| `vthMN`     | 0        | NMOS threshold offset added to `vth0` (V).        |
| `vthMPE`    | 0        | ESD PMOS threshold offset (V).                    |
| `vthMNE`    | 0        | ESD NMOS threshold offset (V).                    |
| `magRR`     | 1        | HV `F_RR` sheet-resistance multiplier.            |
| `magRS`     | 1        | Poly `F_RS` sheet-resistance multiplier.          |
| `magCSIO`   | 1        | `F_CSIO` capacitance multiplier.                  |

## Engineering offset values

The offsets are deliberately symmetric, large enough to be observable in a
ring-oscillator or inverter-chain simulation, and documented per corner in the
file header. They are not Monte-Carlo samples and carry no statistical weight.

- Threshold shift magnitude: ±50 mV per device polarity.
- Resistor spread: ±10 % (`magRR`, `magRS`).
- Capacitor spread: ±10 % (`magCSIO`).

"Slow" = higher |Vth| (weaker drive) + high-R + low-C is NOT bundled; each
corner file lists its own combination explicitly so the mapping is auditable.
