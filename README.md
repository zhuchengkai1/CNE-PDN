# CNE-PDN:

This project introduces a joint optimization framework tailored for 2.5D ICs. By leveraging a neural network surrogate model to replace time-consuming full electromagnetic (EM) simulations, it rapidly extracts equivalent circuit parameters to co-optimize the 3D dimensions of the Power Delivery Network (PDN) and the Through-Silicon Via (TSV) layout.

It effectively resolves two major bottlenecks: the prohibitively slow speed of traditional EM simulations that hinders early-stage iterative optimization, and the accuracy loss inherent in empirical analytical models that fail to capture complex EM coupling. Consequently, this framework efficiently mitigates Dynamic Voltage Drop (DVD) issues, thereby preventing system performance degradation.



## About The Project

**CNE-PDN** is an automated, joint optimization framework designed to maximize the performance of 2.5D heterogeneous Integrated Circuits (ICs). It addresses the critical challenge of **Dynamic Voltage Drop (DVD)**, which degrades system throughput due to high transient currents drawn by massive synchronous computing cores.

Traditionally, early-stage iterative optimization of the Power Delivery Network (PDN) is bottlenecked by the prohibitively slow speed of full electromagnetic (EM) simulations. Conversely, simplified empirical analytical models fail to accurately capture complex EM coupling across diverse PDN topologies, leading to significant accuracy loss.

To overcome these limitations, this project introduces a **Component-Level Neural Parasitic Extraction (CNE)** methodology. We leverage a physics-informed neural surrogate model to replace iterative EM extraction, directly mapping 3D PDN geometries to equivalent circuit parameters with high fidelity (achieving ~97% accuracy at a 380x+ speedup). This exceptional efficiency empowers our advanced optimization algorithm (**BP-tSSBO**) to seamlessly co-optimize both continuous 3D PDN dimensions and discrete Through-Silicon Via (TSV) layouts, while strictly adhering to practical routing-congestion and keepout constraints.



## repository Structure

```text
.
├── opt/             # Source code for the BP-tSSBO optimization algorithm and AIFM evaluation module
├── sim/             # Code for the PARP surrogate model 
├── dataset/         # Training and testing datasets (to be uploaded incrementally after sanitization)
└── README.md        # Project documentation
```



## Optimization algorithm

```text
opt/
├── src/             # Open-source core implementation of the tSS-BO algorithm
├── circuit.py       # Script for editing and generating circuit .sp netlist files
├── hspice_gpt.py    # Module for invoking HSPICE, parsing .sp netlists, and reading .ac0 frequency response data
├── tss_tsv.py       # BP-tSSBO framework for pure TSV layout optimization with AIFM evaluation (manual keep-out zones)
├── tss_tsv_final.py # BP-tSSBO framework for joint TSV layout and 3D PDN geometry co-optimization with AIFM evaluation (manual keep-out zones)
└── tss_tsv_route.py # BP-tSSBO framework for joint TSV layout and 3D PDN geometry co-optimization with automated routing keep-out zone generation
```



## PARP surrogate model

```text
sim/
├── circuit.py               # Script for editing and generating circuit .sp netlist files
├── circuit_end.py           # Script for editing the final test .sp circuit netlist files
├── em_simulation.py         # Script for invoking and modeling HFSS simulations
├── em_simulation2.py        # Script for invoking and modeling the final HFSS test cases
├── geminitarns_final.py     # PARP Surrogate Model: Neural network architecture, training, and batch inference
├── geminitrans_single.py    # PARP Surrogate Model: Interface for rapid single-sample forward inference
├── hspice_gpt.py            # Module for invoking HSPICE, parsing .sp netlists, and reading .ac0 frequency response data
├── hspice_gpt_end.py        # Module for invoking the final HSPICE test code, parsing .sp netlists, and reading .ac0 data
├── main.py                  # Optimization algorithm and test set generation
└── main2.py                 # Optimization algorithm and test set generation result validation
```

