# CNE-PDN:

This project introduces a joint optimization framework tailored for 2.5D ICs. By leveraging a neural network surrogate model to replace time-consuming full electromagnetic (EM) simulations, it rapidly extracts equivalent circuit parameters to co-optimize the 3D dimensions of the Power Delivery Network (PDN) and the Through-Silicon Via (TSV) layout.

It effectively resolves two major bottlenecks: the prohibitively slow speed of traditional EM simulations that hinders early-stage iterative optimization, and the accuracy loss inherent in empirical analytical models that fail to capture complex EM coupling. Consequently, this framework efficiently mitigates Dynamic Voltage Drop (DVD) issues, thereby preventing system performance degradation.



## About The Project

**CNE-PDN** is an automated, joint optimization framework designed to maximize the performance of 2.5D heterogeneous ICs. It addresses the critical challenge of DVD, which degrades system throughput due to high transient currents drawn by massive synchronous computing cores.

Traditionally, early-stage iterative optimization of the PDN is bottlenecked by the prohibitively slow speed of full EM simulations. Conversely, simplified empirical analytical models fail to accurately capture complex EM coupling across diverse PDN topologies, leading to significant accuracy loss.

To overcome these limitations, this project introduces a CNE methodology. We leverage a physics-informed neural surrogate model to replace iterative EM extraction, directly mapping 3D PDN geometries to equivalent circuit parameters with high fidelity (achieving ~97% accuracy at a 380x+ speedup). This exceptional efficiency empowers our advanced optimization algorithm (BP-tSSBO) to seamlessly co-optimize both continuous 3D PDN dimensions and discrete Through-Silicon Via (TSV) layouts, while strictly adhering to practical routing-congestion and keepout constraints.



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



## Supplementary experiment

> **Note:** All corresponding figures and visualizations for the following experiments are provided in the `Appendix/` directory of this repository.

## 📊 Supplementary Experiments

> **Note:** All corresponding figures and visualizations for the following experiments are provided in the `Appendix/` directory of this repository.

### Supplementary Experiment 1: Scalability Testing on Industrial Cases

Due to the strict time limits of the rebuttal period, exhaustive multi-round benchmarking was constrained. However, single-round tests on significantly larger industrial configurations definitively demonstrate the scalability and effectiveness of our framework.

* **Case 1: A $36 \times 36$ grid with $256$ TSVs across $8$ chiplets.** As shown in **Figure 1**, the system $F_{\max}$ improved from $2.100\text{ GHz}$ to $2.131\text{ GHz}$. Considering this is a massive $1296$-dimensional optimization problem, achieving a $0.031\text{ GHz}$ gain is a highly substantial achievement that proves the effectiveness of our workflow. **Figure 3** visualizes the optimal TSV layout generated for this case, detailing the chiplet placement, routing status, and Keep-Out Zone (KOZ) arrangements.

* **Case 2: A $48 \times 48$ grid with $512$ TSVs across $12$ chiplets.** As illustrated in **Figure 2**, the $F_{\max}$ increased from $2.070\text{ GHz}$ to $2.089\text{ GHz}$. For an extremely complex $2304$-dimensional optimization space, securing a $0.019\text{ GHz}$ improvement remains an impressive result, further validating the robustness of our approach at scale. **Figure 4** visualizes the corresponding optimal TSV layout, mapping the chiplet locations, routing paths, and KOZ boundaries.

---

### Supplementary Experiment 2: High-Dimensional Algorithm Benchmarking

**Figure 5** presents the optimization performance on a $531$-dimensional Ackley function. Because our physical framework relies on Synopsys HSPICE—a commercial simulator that acts as a strictly non-differentiable "black box"—gradient-based optimization algorithms are entirely inapplicable. 

To rigorously test our mathematical engine, we adopted the Ackley function (notoriously difficult due to its vast search space and dense local optima) as a proxy. The benchmark results clearly demonstrate that our BP-tSSBO algorithm significantly and consistently outperforms other baseline algorithms in navigating complex, high-dimensional spaces.

---

### Supplementary Experiment 3: Sensitivity Analysis

* **Case 1: Impact of Macro-Block Size Variations.** As shown in **Figure 6**, evaluations on a $23 \times 23$ grid reveal that the $2 \times 2$ macro-block configuration yields the best optimization performance. Compared to a $1 \times 1$ configuration (which represents the absence of macro-blocking, operating directly in the fine-grained continuous space), the $2 \times 2$ setup exhibits significantly stronger optimization capabilities during Stage 2. This strongly justifies the integration of the macro-blocking strategy.

* **Case 2: Impact of TSV Quantity Variations.** As shown in **Figure 7**, tests conducted on the $23 \times 23$ grid with varying total TSV counts ($60$, $80$, $100$, $120$, and $140$) consistently yield excellent optimization gains. This confirms that the algorithm is highly adaptable to a wide range of design density constraints and initial layouts.

---

### Supplementary Experiment 4: Error Propagation & Sensitivity of $F_{\max}$

To address concerns regarding whether PARP extraction errors cause significant deviations in the final $F_{\max}$, we conducted a rigorous Error Propagation and Sensitivity Analysis.

**Part 1: Evaluation based on actual PARP predictions**

* **Actual PARP Impedance Error (MAPE):** $2.68\%$
* **Ground Truth:** Supply Voltage = $0.6777\text{ V}$ | $F_{\max}$ = $1.7837\text{ GHz}$
* **PARP Prediction:** Supply Voltage = $0.6853\text{ V}$ | $F_{\max}$ = $1.8558\text{ GHz}$
* **Conclusion:** A $2.68\%$ impedance error from PARP translates to a final $F_{\max}$ error of only $4.04\%$.

**Part 2: Standard Artificial Error Injection (Robustness Test)**
We globally deteriorated the baseline impedance by $+5\%$, $+10\%$, and $+20\%$ to observe the system's robustness:

* **$+5\%$ Error:** Voltage drops to $0.6766\text{ V}$ | $F_{\max}$ = $1.7732\text{ GHz}$ | Performance loss: $0.59\%$
* **$+10\%$ Error:** Voltage drops to $0.6755\text{ V}$ | $F_{\max}$ = $1.7627\text{ GHz}$ | Performance loss: $1.17\%$
* **$+20\%$ Error:** Voltage drops to $0.6733\text{ V}$ | $F_{\max}$ = $1.7419\text{ GHz}$ | Performance loss: $2.34\%$

**Summary:** The error does not propagate linearly. This is because the AIFM module processes the broadband frequency spectrum via IFFT, which naturally smooths out localized errors. Furthermore, as long as the chip operates within a healthy voltage range, the Alpha-Power Law provides a non-linear buffering effect, preventing the final $F_{\max}$ from being overly sensitive to minor impedance variations.
