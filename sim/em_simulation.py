import ansys.aedt.core
import time
import os
import tempfile
import platform 
import traceback
import pandas as pd
import numpy as np
# x: width, y: lenth, z: thickness

def normal_until_in_range(low, high, mean, std):
    while True:
        x = np.random.normal(mean, std)
        if low <= x <= high:
            return x

def combine_re_im_into_data(z11_tmp_data_file, z11_tmp_re_file, z11_tmp_im_file):
    # === 1. read CSV file ===
    df_mag = pd.read_csv(z11_tmp_data_file, sep=';', engine='python')
    df_re = pd.read_csv(z11_tmp_re_file, sep=';', engine='python')
    df_im = pd.read_csv(z11_tmp_im_file, sep=';', engine='python')

    # === 2.  freq ===
    re_vals = df_re.iloc[:, 1].values
    im_vals = df_im.iloc[:, 1].values

    # === 3.  dB20 ===
    eps = 1e-18
    re_db = 20 * np.log10(np.abs(re_vals) + eps)
    im_db = 20 * np.log10(np.abs(im_vals) + eps)

    # === 4.  CSV（3  4 ）===
    df_mag["Re_dB"] = re_db
    df_mag["Im_dB"] = im_db

    # === 5. save to old file ===
    df_mag.to_csv(z11_tmp_data_file, index=False)
    print(f"[OK]  dB20(Re) and dB20(Im) to：{z11_tmp_data_file}")

def em_simulation(project_dir,
                  z11_tmp_data_file,
                  experiment_index,
                  experiment_iter,
                  net
                  ):
    '''call hfss simulation and save S params to csv files'''
    z11_tmp_re_file = "***"
    z11_tmp_im_file = "***"
    # check os
    system_name = platform.system().lower() 
    if system_name == "windows":

        os.environ["ANSYSEM_ROOT232"] = r"***"

        HFSS_VERSION = "2025.1"
        NUM_CORES = 4
    elif system_name == "linux":
        HFSS_VERSION = "2024.1"
        NUM_CORES = 1

    # dir setting
    PROJECT_NAME = os.path.basename(os.path.normpath(f"{project_dir}_{experiment_iter}_project"))
    DESIGN_NAME = os.path.basename(os.path.normpath(f"{project_dir}_{experiment_iter}_design"))
    temp_folder = tempfile.TemporaryDirectory(suffix=".ansys")
    tmp_dir = os.path.join(project_dir, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    result_dir = os.path.join(tmp_dir, experiment_index)
    os.makedirs(result_dir, exist_ok=True)
    
    # set ansys params
    NO_GUI = False
    PRINT_ON = True
    # SOLUTION_TYPE = "Modal"
    SOLUTION_TYPE = "Terminal"
    
    # launch ansys simulation
    start_time = time.time()
    ansys.aedt.core.Desktop(version=HFSS_VERSION, non_graphical=NO_GUI, new_desktop=True, close_on_exit=False, student_version=False)
    hfss = ansys.aedt.core.Hfss(project=PROJECT_NAME, design=DESIGN_NAME, solution_type=SOLUTION_TYPE, non_graphical=NO_GUI)

    if PRINT_ON == True:
        if hfss.design_name is None:
            print("Design creation failed.")
        else:
            print(f"Design '{hfss.design_name}' created successfully.")
        
    # set unit
    hfss.modeler.model_units = "um"

    # substrate shape and creation

    # pdn_wide = normal_until_in_range(6,20,12,2.3)
    # space = normal_until_in_range(6, 20, 12, 2.3)
    # h_si = normal_until_in_range(30, 75, 50, 8.3)
    # h_sio = normal_until_in_range(0.25, 1.3, 0.75, 0.226)
    # h_pdn_1 = h_pdn_2 = normal_until_in_range(0.6, 1.5, 1, 0.3)
    # h_sio2 = normal_until_in_range(0.6, 1.5, 1, 0.3)

    pdn_wide = 16
    space = 12
    h_si = 50
    h_sio = 0.75
    h_pdn_1 = h_pdn_2 = 1
    h_sio2 = 1


    file_path = os.path.join(result_dir, "data.csv")

    params = {
        "pdn_wide": pdn_wide,
        "space": space,
        "h_si": h_si,
        "h_sio": h_sio,
        "h_pdn_1": h_pdn_1,
        "h_sio2": h_sio2,
        "net": net,
        "h_pdn_2": h_pdn_2
    }

    # write in
    with open(file_path, "w") as f:
        for key, value in params.items():
            f.write(f"{key}\t{value}\n")

    # dielectric layer shape

    # dielectric layer shape
    # ox_w = 4*pdn_wide + 4*space
    # ox_l = 4*pdn_wide + 4*space
    # ox_h = h_si

    hfss.modeler.create_box([0, 0, 0],
                            [2 * net * pdn_wide + (2 * net + 1) * space, 2 * net * pdn_wide + (2 * net + 1) * space,
                             h_si],
                            name="Substrate",
                            material="silicon")

    hfss.modeler.create_box([0, 0, h_si],
                            [2 * net * pdn_wide + (2 * net + 1) * space, 2 * net * pdn_wide + (2 * net + 1) * space,
                             h_sio],
                            name="middle_1",
                            material="silicon_dioxide")

    hfss.modeler.create_box([0, 0, h_si + h_sio + h_pdn_1],
                            [2 * net * pdn_wide + (2 * net + 1) * space, 2 * net * pdn_wide + (2 * net + 1) * space,
                             h_sio2],
                            name="middle_2",
                            material="silicon_dioxide")

    # hfss.modeler.create_box([0, 0, h_si + h_sio],
    #                         [2*net * pdn_wide + 2*net* space, pdn_wide/2, h_pdn_1],
    #                         name="pdn_1_0",
    #                         material="copper")
    #
    # hfss.modeler.create_box([0, 2*net * pdn_wide + 2*net * space - pdn_wide/2, h_si + h_sio],
    #                         [2*net * pdn_wide + 2*net * space, pdn_wide/2, h_pdn_1],
    #                         name=f"pdn_1_{2*net}",
    #                         material="copper")
    #
    # hfss.modeler.create_box([0, 0, h_si + h_sio + h_pdn_1 + h_sio2],
    #                         [pdn_wide/2, 2*net * pdn_wide + 2*net* space, h_pdn_1],
    #                         name="pdn_2_0",
    #                         material="copper")
    #
    # hfss.modeler.create_box([2*net * pdn_wide + 2*net* space - pdn_wide/2, 0, h_si + h_sio],
    #                         [pdn_wide/2, 2*net * pdn_wide + 2*net* space, h_pdn_1],
    #                         name=f"pdn_2_{2*net}",
    #                         material="copper")
    for i in range(2 * net):
        hfss.modeler.create_box([0, (i + 1) * space + i * pdn_wide, h_si + h_sio],
                                [2 * net * pdn_wide + (2 * net + 1) * space, pdn_wide, h_pdn_1],
                                name=f"pdn_1_{i + 1}",
                                material="copper")

    for i in range(2 * net + 1):
        hfss.modeler.create_box([0, i * space + i * pdn_wide, h_si + h_sio],
                                [2 * net * pdn_wide + (2 * net + 1) * space, space, h_pdn_1],
                                name=f"space_1_{i + 1}",
                                material="polyimide")

    for i in range(2 * net):
        hfss.modeler.create_box([(i + 1) * space + i * pdn_wide, 0, h_si + h_sio + h_pdn_1 + h_sio2],
                                [pdn_wide, 2 * net * pdn_wide + (2 * net + 1) * space, h_pdn_2],
                                name=f"pdn_2_{i + 1}",
                                material="copper")
    for i in range(2 * net + 1):
        hfss.modeler.create_box([i * space + i * pdn_wide, 0, h_si + h_sio + h_pdn_1 + h_sio2],
                                [space, 2 * net * pdn_wide + (2 * net + 1) * space, h_pdn_2],
                                name=f"space_2_{i + 1}",
                                material="polyimide")

    # create port
    for i in range(net - 1):
        if SOLUTION_TYPE == "Modal":
            hfss.modeler.create_rectangle(
                orientation=ansys.aedt.core.constants.PLANE.YZ,
                origin=[0, (2 * i + 1) * space + (2 * i + 1) * pdn_wide, h_si + h_sio],
                sizes=[space, h_pdn_1],
                name=f"port_1_1_{i + 1}"
            )
            hfss.lumped_port(assignment=f"port_1_1_{i + 1}",
                             integration_line=[[0, space * 2 + pdn_wide * 3 / 2 + i * 2 * space + 2 * i * pdn_wide,
                                                h_si + h_sio + h_pdn_1 / 2],
                                               [0, space + pdn_wide / 2 + i * 2 * space + 2 * i * pdn_wide,
                                                h_si + h_sio + h_pdn_1 / 2]],
                             terminals_rename=False)
            # 2
            hfss.modeler.create_rectangle(
                orientation=ansys.aedt.core.constants.PLANE.YZ,
                origin=[2 * net * pdn_wide + (2 * net + 1) * space, (2 * i + 1) * space + (2 * i + 1) * pdn_wide,
                        h_si + h_sio],
                sizes=[space, h_pdn_1],
                name=f"port_1_2_{i + 1}"
            )
            hfss.lumped_port(assignment=f"port_1_2_{i + 1}",
                             integration_line=[[2 * net * pdn_wide + (2 * net + 1) * space,
                                                space * 2 + pdn_wide * 3 / 2 + i * 2 * space + 2 * i * pdn_wide,
                                                h_si + h_sio + h_pdn_1 / 2],
                                               [2 * net * pdn_wide + (2 * net + 1) * space,
                                                space + pdn_wide / 2 + i * 2 * space + 2 * i * pdn_wide,
                                                h_si + h_sio + h_pdn_1 / 2]],
                             terminals_rename=False)

            # 3
            hfss.modeler.create_rectangle(
                orientation=ansys.aedt.core.constants.PLANE.XZ,
                origin=[(2 * i + 1) * space + (2 * i + 1) * pdn_wide, 0, h_si + h_sio + h_pdn_1 + h_sio2],
                sizes=[space, h_pdn_1],
                name=f"port_2_1_{i + 1}"
            )
            hfss.lumped_port(assignment=f"port_2_1_{i + 1}",
                             integration_line=[[space * 2 + pdn_wide * 3 / 2 + i * 2 * space + 2 * i * pdn_wide, 0,
                                                h_si + h_sio + h_pdn_1 + h_sio2 + h_pdn_2 / 2],
                                               [space + pdn_wide / 2 + i * 2 * space + 2 * i * pdn_wide, 0,
                                                h_si + h_sio + h_pdn_1 + h_sio2 + h_pdn_2 / 2]],
                             terminals_rename=False)
            # 4
            hfss.modeler.create_rectangle(
                orientation=ansys.aedt.core.constants.PLANE.XZ,
                origin=[(2 * i + 1) * space + (2 * i + 1) * pdn_wide, 2 * net * pdn_wide + (2 * net + 1) * space,
                        h_si + h_sio + h_pdn_1 + h_sio2],
                sizes=[space, h_pdn_1],
                name=f"port_2_2_{i + 1}"
            )
            hfss.lumped_port(assignment=f"port_2_2_{i + 1}",
                             integration_line=[[space * 2 + pdn_wide * 3 / 2 + i * 2 * space + 2 * i * pdn_wide,
                                                2 * net * pdn_wide + (2 * net + 1) * space,
                                                h_si + h_sio + h_pdn_1 + h_sio2 + h_pdn_2 / 2],
                                               [space + pdn_wide / 2 + i * 2 * space + 2 * i * pdn_wide,
                                                2 * net * pdn_wide + (2 * net + 1) * space,
                                                h_si + h_sio + h_pdn_1 + h_sio2 + h_pdn_2 / 2]],
                             terminals_rename=False)
        elif SOLUTION_TYPE == "Terminal":
            hfss.modeler.create_rectangle(
                orientation=ansys.aedt.core.constants.PLANE.YZ,
                origin=[0, (2 * i + 1) * space + (2 * i + 1) * pdn_wide, h_si + h_sio],
                sizes=[space, h_pdn_1],
                name=f"port_1_1_{i + 1}"
            )

            hfss.lumped_port(assignment=f"port_1_1_{i + 1}",
                             reference=f"pdn_1_{i * 2 + 1}",
                             integration_line=hfss.AxisDir.ZNeg,
                             name=f"port_1_1_{i + 1}",
                             terminals_rename=True)
            # 2
            hfss.modeler.create_rectangle(
                orientation=ansys.aedt.core.constants.PLANE.YZ,
                origin=[2 * net * pdn_wide + (2 * net + 1) * space, (2 * i + 1) * space + (2 * i + 1) * pdn_wide,
                        h_si + h_sio],
                sizes=[space, h_pdn_1],
                name=f"port_1_2_{i + 1}"
            )

            hfss.lumped_port(assignment=f"port_1_2_{i + 1}",
                             reference=f"pdn_1_{i * 2 + 1}",
                             integration_line=hfss.AxisDir.ZNeg,
                             name=f"port_1_2_{i + 1}",
                             terminals_rename=True)

            # 3
            hfss.modeler.create_rectangle(
                orientation=ansys.aedt.core.constants.PLANE.ZX,
                origin=[(2 * i + 1) * space + (2 * i + 1) * pdn_wide, 0, h_si + h_sio + h_pdn_1 + h_sio2],
                sizes=[ h_pdn_1,space],
                name=f"port_2_1_{i + 1}"
            )

            hfss.lumped_port(assignment=f"port_2_1_{i + 1}",
                             reference=f"pdn_2_{i * 2 + 1}",
                             integration_line=hfss.AxisDir.XNeg,
                             name=f"port_2_1_{i + 1}",
                             terminals_rename=True)

            # 4
            hfss.modeler.create_rectangle(
                orientation=ansys.aedt.core.constants.PLANE.ZX,
                origin=[(2 * i + 1) * space + (2 * i + 1) * pdn_wide, 2 * net * pdn_wide + (2 * net + 1) * space,
                        h_si + h_sio + h_pdn_1 + h_sio2],
                sizes=[ h_pdn_1,space],
                name=f"port_2_2_{i + 1}"
            )

            hfss.lumped_port(assignment=f"port_2_2_{i + 1}",
                             reference=f"pdn_2_{i * 2 + 1}",
                             integration_line=hfss.AxisDir.XNeg,
                             name=f"port_2_2_{i + 1}",
                             terminals_rename=True)

        # unite all copper pixel

    # create airbox and set BC
    hfss.modeler.create_box([-pdn_wide, -pdn_wide, -h_si / 2],
                            [(2 * net + 2) * pdn_wide + (2 * net + 1) * space,
                             (2 * net + 2) * pdn_wide + (2 * net + 1) * space, 2 * h_si],
                            name="airbox",
                            material="air",
                            )

    hfss.assign_radiation_boundary_to_objects("airbox")
    
    hfss.change_material_override()

    # create simulation setup
    setup = hfss.create_setup(name="setup")
    
    # frequency sweep setting
    # setup.props["Frequency"] = "100GHz"
    # setup.props["MaxDeltaS"] = 0.05
    # setup.props["MaximumPasses"] = 10
    # setup.props["PercentRefinement"] = 30
    # setup.props["MinimumConvergedPasses"] = 1
    # setup.props["MinimumPasses"] = 1
    # setup.props["SolveType"] = "Iterative"
    # frequency sweep setting
    setup.props["Frequency"] = "30GHz"
    setup.props["MaxDeltaS"] = 0.05
    setup.props["MaximumPasses"] = 10
    setup.props["PercentRefinement"] = 30
    setup.props["MinimumConvergedPasses"] = 1
    setup.props["MinimumPasses"] = 1
    setup.update()

    # initialize frequency sweep
    hfss.create_linear_count_sweep(
        setup="setup",
        units="GHz",
        start_frequency=0.001,
        stop_frequency=50,
        num_of_freq_points=100,
        sweep_type="Interpolating",
    )
    # sleep

    # start simulation
    solution_condition = hfss.analyze(cores=NUM_CORES)

    if solution_condition == True:
        try:
            # ===== 1.  =====
            z21_mag = hfss.post.get_solution_data(
                expressions=["dB20(Zt(port_1_2_1_T1, port_1_1_1_T1))"]
            )
            z21_re = hfss.post.get_solution_data(
                expressions=["re(Zt(port_1_2_1_T1, port_1_1_1_T1))"]
            )
            z21_im = hfss.post.get_solution_data(
                expressions=["im(Zt(port_1_2_1_T1, port_1_1_1_T1))"]
            )


            z21_mag.export_data_to_csv(os.path.join(result_dir, z11_tmp_data_file))
            z21_re.export_data_to_csv(os.path.join(result_dir, z11_tmp_re_file))
            z21_im.export_data_to_csv(os.path.join(result_dir, z11_tmp_im_file))

            combine_re_im_into_data(
                os.path.join(result_dir, z11_tmp_data_file),
                os.path.join(result_dir, z11_tmp_re_file),
                os.path.join(result_dir, z11_tmp_im_file)
            )

        except Exception as e:
            print(f"[Error] Failed to export terminal impedance data: {e}")
            traceback.print_exc()

    hfss.close_project()
    hfss.clean_proj_folder()
    hfss.release_desktop()
    temp_folder.cleanup()
    end_time = time.time()
    elapsed_time = end_time - start_time

    if PRINT_ON == True:
        print(f"simulation time : {elapsed_time:.6f}s")
        
    return solution_condition, result_dir


    if __name__ == "__main__":
        net = 5
        # net = 23

        current_time = time.localtime()
        date = f"{current_time.tm_year % 100}{current_time.tm_mon}{current_time.tm_mday}_{current_time.tm_hour:02d}{current_time.tm_min:02d}"
        experiment_index = f"{date}"
        experiment_iter = "1"
        src_path = os.path.abspath(__file__)  # data_generation.py
        project_dir = os.path.dirname(src_path)
        s12_tmp_data_file = "s12_output.csv"

        sim_start_time = time.time()
        solution_condition, result_dir = em_simulation(project_dir,
                                                       s12_tmp_data_file,
                                                       experiment_index,
                                                       experiment_iter,
                                                       net
                                                       )
        print(result_dir)