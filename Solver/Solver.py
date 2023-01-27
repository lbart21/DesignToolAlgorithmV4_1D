"""
Function:
Author: Luke Bartholomew
Edits:
"""
from Algorithms.DesignToolAlgorithmV4_1D.Solver.WriteToDataFile import write_to_data_file
from Algorithms.DesignToolAlgorithmV4_1D.Solver.WriteCellDataToFile import write_cell_data_to_file
from Algorithms.DesignToolAlgorithmV4_1D.Solver.WriteInterfaceDataToFile import write_interface_data_to_file
from Algorithms.DesignToolAlgorithmV4_1D.Integrate.Integrate import Integrate
from copy import deepcopy
class Solver():
    def __init__(self, mesh_object, cfl_flag, t_final, data_save_dt, transient_cell_flow_property_variables_to_write, \
                        transient_interface_flow_property_variables_to_write, \
                        spatial_cell_flow_property_variables_to_write, rapid_data_save_steps) -> None:
        """
        meshObject = object with attributes: cell_array, interface_array, map_cell_id_to_west_interface_idx, 
        cfl_flag = [Bool, float]
        labels = 
        """
        t_current = 0.0
        write_to_data_file(cellArray = mesh_object.cell_array, time = t_current, labels = mesh_object.component_labels, \
                        flow_property_variables = spatial_cell_flow_property_variables_to_write)
        for cell_id in mesh_object.cell_idx_to_track:
            write_cell_data_to_file(cell = mesh_object.cell_array[cell_id], time = t_current, \
                                flow_property_variables = transient_cell_flow_property_variables_to_write)
        
        time_tol = 1e-9
        t_write_tol = 1e-9
        t_write = data_save_dt
        written_data = False
        rapid_data_written = False
        current_mesh_object = mesh_object
        current_step = 0
        while t_current < t_final and abs(t_current - t_final) > time_tol:
            new_data = Integrate(mesh = current_mesh_object, cfl_flag = cfl_flag, t_current = t_current, current_step = current_step)
            t_current += new_data.dt_total
            written_data = False
            rapid_data_written = False
            if t_current > t_write - t_write_tol:
                print("Writing data, t = ", t_current)
                write_to_data_file(cellArray = new_data.mesh.cell_array, time = t_current, labels = new_data.mesh.component_labels, \
                                flow_property_variables = spatial_cell_flow_property_variables_to_write)
                written_data = True
                t_write += data_save_dt
            
            current_mesh_object = new_data.mesh
            current_step += 1
            if current_step % rapid_data_save_steps == 0:
                for cell_id in new_data.mesh.cell_idx_to_track:
                    write_cell_data_to_file(cell = new_data.mesh.cell_array[cell_id], time = t_current, \
                                        flow_property_variables = transient_cell_flow_property_variables_to_write)
                for interface_id in new_data.mesh.interface_idx_to_track:
                    #print(interfaceID)
                    write_interface_data_to_file(interface = new_data.mesh.interface_array[interface_id], time = t_current - new_data.dt_total, \
                                                flow_property_variables = transient_interface_flow_property_variables_to_write)
                rapid_data_written = True
            
        if not written_data:
            write_to_data_file(cellArray = current_mesh_object.cell_array, time = t_current, \
                            labels = current_mesh_object.component_labels, \
                            flow_property_variables = spatial_cell_flow_property_variables_to_write)
        
        if not rapid_data_written:
            for cell_id in new_data.mesh.cell_idx_to_track:
                write_cell_data_to_file(cell = new_data.mesh.cell_array[cell_id], time = t_current, \
                                    flow_property_variables = transient_cell_flow_property_variables_to_write)
            for interface_id in new_data.mesh.interface_idx_to_track:
                write_interface_data_to_file(interface = new_data.mesh.interface_array[interface_id], \
                                    time = t_current - new_data.dt_total, \
                                    flow_property_variables = transient_interface_flow_property_variables_to_write)
        