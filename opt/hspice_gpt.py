import subprocess
import pandas as pd
import matplotlib.pyplot as plt
import os
import shutil
import numpy as np
import glob
import circuit
import csv


HSPICE_PATH = r"***"
# SP_FILE = "inverter.sp"

SP_FILE = f"inverter_net_{os.getpid()}.sp"



def read_ac0_fixed_width(ac0_file, OUTPUT_DIR, num_length=13):

    with open(ac0_file, 'r') as f:
        lines = f.readlines()

    print(f" AC : {ac0_file}")
    print(f"{num_length} ")
    lines = lines[5:]
    numbers = []

    for line in lines:
        line = line.rstrip("\n")
        for i in range(0, len(line), 13):
            chunk = line[i:i + 13].strip()
            if chunk:
                numbers.append(chunk)

    rows = [numbers[i:i + 9] for i in range(0, len(numbers), 9)]
    output_csv = os.path.join(OUTPUT_DIR, "my.csv")

    with open(output_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)


def data_deal(my_file, OUTPUT_DIR):
    df = pd.read_csv(my_file, header=None,
                     names=['freq', 'V_2_2re', 'V_2_2im', 'V_7_15re', 'V_7_15im', 'V_15_4re', 'V_15_4im',
                            'I_re', 'I_im'])

    V_2_2 = df['V_2_2re'].to_numpy() + 1j * df['V_2_2im'].to_numpy()
    V_7_15 = df['V_7_15re'].to_numpy() + 1j * df['V_7_15im'].to_numpy()
    V_15_4 = df['V_15_4re'].to_numpy() + 1j * df['V_15_4im'].to_numpy()
    I = df['I_re'].to_numpy() + 1j * df['I_im'].to_numpy()


    I_safe = I.copy()
    I_safe[np.abs(I_safe) < 1e-30] = 1e-30

    Z_2_2 = V_2_2 / I_safe
    Z_mag_2_2 = np.abs(Z_2_2)
    Z_dB20_2_2 = 20 * np.log10(Z_mag_2_2 + 1e-30)

    Z_7_15 = V_7_15 / I_safe
    Z_mag_7_15 = np.abs(Z_7_15)
    Z_dB20_7_15 = 20 * np.log10(Z_mag_7_15 + 1e-30)

    Z_15_4 = V_15_4 / I_safe
    Z_mag_15_4 = np.abs(Z_15_4)
    Z_dB20_15_4 = 20 * np.log10(Z_mag_15_4 + 1e-30)

    df_out = pd.DataFrame({
        'freq': df['freq'],
        'Z_re_2_2': np.real(Z_2_2),
        'Z_im_2_2': np.imag(Z_2_2),
        'Z_mag_2_2': Z_dB20_2_2,
        'Z_re_7_15': np.real(Z_7_15),
        'Z_im_7_15': np.imag(Z_7_15),
        'Z_mag_7_15': Z_dB20_7_15,
        'Z_re_15_4': np.real(Z_15_4),
        'Z_im_15_4': np.imag(Z_15_4),
        'Z_mag_15_4': Z_dB20_15_4,
        'Z_phase_deg_2_2': np.angle(Z_2_2, deg=True)
    })

    output_csv = os.path.join(OUTPUT_DIR, "result.csv")
    df_out.to_csv(output_csv, index=False)



def plot_ac_response(df, node_name="node_1_1"):

    if df.empty:
        print("error")
        return

    mag_min, mag_max = df["Mag"].min(), df["Mag"].max()

    print(f"from{mag_min:.2e} to {mag_max:.2e}")

    if mag_max < 1e-10:
        print("dB")
        df["Mag_dB"] = 20 * np.log10(np.maximum(df["Mag"], 1e-100))

        fig, ax1 = plt.subplots(1, 1, figsize=(10, 4))

        ax1.semilogx(df["Freq(Hz)"], df["Mag_dB"], 'b-', linewidth=2)
        ax1.set_xlabel("Frequency (Hz)")
        ax1.set_ylabel("Magnitude (dB)")
        ax1.grid(True, which="both", ls="--", alpha=0.7)
        ax1.set_title(f"AC Magnitude Response at {node_name} (dB)")

        plt.show()

    else:
        fig, ax1 = plt.subplots(1, 1, figsize=(5, 8))

        ax1.loglog(df["Freq(Hz)"], df["Mag"], 'b-', linewidth=2)
        ax1.set_xlabel("Frequency (Hz)")
        ax1.set_ylabel("Magnitude |V|")
        ax1.grid(True, which="both", ls="--", alpha=0.7)
        ax1.set_title(f"AC Magnitude Response at {node_name}")

        plt.show()


def hspice_run(L_AX, R_AX, C_psi, C_sub, R_sub, L_BX, R_BX, C_pgbx, L_CX, R_CX, C_cont, C_insulator, C_bump,
               C_tsv, L_total, R_tsv, C_total, R_dc, R_ac, net, C_pgcx, C_pgax, OUTPUT_DIR, place):
    flag = 0
    circuit.example_usage(L_AX, R_AX, C_psi, C_sub, R_sub, L_BX, R_BX, C_pgbx, L_CX, R_CX, C_cont, C_insulator,
                          C_bump, C_tsv, L_total, R_tsv, C_total, R_dc, R_ac, net, C_pgcx, C_pgax, SP_FILE,
                          place)

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"create output: {OUTPUT_DIR}")
    else:
        print(f"output: {OUTPUT_DIR}")
        for file in glob.glob(os.path.join(OUTPUT_DIR, "inverter.*")):
            try:
                os.remove(file)
                print(f"delete old: {file}")
            except Exception as e:
                print(f"delete {file} error: {e}")



    if not os.path.exists(SP_FILE):
        print(f"error: SP {SP_FILE} none!")
        exit(1)

    try:
        result = subprocess.run([HSPICE_PATH, SP_FILE],
                                capture_output=True,
                                text=True,
                                shell=True)

        print(f"HSPICE : {result.returncode}")

        if result.returncode == 0:
            print("HSPICE success!")
        else:
            print(f"HSPICE wrong: {result.returncode}")
            if result.stderr:
                print(f"error: {result.stderr}")

    except Exception as e:
        print(f"HSPICE error: {e}")
        exit(1)

    sp_prefix = os.path.splitext(SP_FILE)[0]

    print("move to output...")
    files_moved = 0

    for file in os.listdir("."):
        if file.startswith(sp_prefix):
            try:
                shutil.move(file, os.path.join(OUTPUT_DIR, file))
                files_moved += 1
                print(f"move file: {file}")
            except Exception as e:
                print(f"move file {file} error: {e}")

    print(f"move {files_moved} file to {OUTPUT_DIR}")

    AC0_FILE = os.path.join(OUTPUT_DIR, f"{sp_prefix}.ac0")
    my_file = os.path.join(OUTPUT_DIR, "my.csv")

    if not os.path.exists(AC0_FILE):
        flag = 1
        print(f"error: {AC0_FILE}")
        print("check:")
        return OUTPUT_DIR, flag

    print(f"find AC output: {AC0_FILE}")

    read_ac0_fixed_width(AC0_FILE, OUTPUT_DIR, num_length=13)
    data_deal(my_file, OUTPUT_DIR)
    return OUTPUT_DIR, flag


if __name__ == "__main__":
    L_AX = 1.0128e-9
    L_BX = 9.0326e-10
    L_CX = 1.07678e-10
    R_AX = 0.001175
    R_BX = 0.00023742
    R_CX = 416.12076
    C_psi = 4.8194e-14
    C_sub = 8.4212e-14
    C_pgax = C_pgbx = C_pgcx = 3.3633e-15
    R_sub = 243.361
    C_cont = 2.253e-14
    C_insulator = 2.915e-13
    C_bump = 2.036e-13
    C_tsv = 9.602e-13
    L_total = 8.994e-12
    R_tsv = 1.097e+03
    C_total = 3.119e-13
    R_dc = 4.546e-02
    R_ac = 5e-6
    net = 23
    work_dir = "aver"
    # os.makedirs(work_dir)
    shutil.rmtree(work_dir)

    place = np.zeros((23, 23))

    output_dir = hspice_run(L_AX, R_AX, C_psi, C_sub, R_sub, L_BX, R_BX, C_pgbx, L_CX, R_CX, C_cont,
                            C_insulator, C_bump, C_tsv, L_total, R_tsv, C_total, R_dc, R_ac, net, C_pgcx,
                            C_pgax, work_dir, place)