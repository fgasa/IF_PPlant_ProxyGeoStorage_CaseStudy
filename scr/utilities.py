import os
import pandas as pd
import numpy as np
from tabulate import tabulate
import CoolProp.CoolProp as CP

WH2GWH = 1e-9
W2MW = 1e-6
SEC2HOUR = 3600
STD_TEMPERATURE = 293.15
STD_PRESSURE = 101325
CP_VERSION = f"-- CoolProp version: {CP.get_global_param_string('version')}\n"
REFERENCE_CONDITION = f"-- Standard temperature: {STD_TEMPERATURE} K, Standard pressure: {STD_PRESSURE} Pa\n"


def read_coupled_sim_rst(file_path):
    '''reads a CSV file from coupled simulation and performs some preprocessing '''
    file_name = os.path.basename(file_path)
    dir_name = os.path.dirname(file_path)
    print('File name:', file_name)
    print('File directory:', dir_name)

    df = pd.read_csv(file_path, sep=';', decimal='.')

    # create boolean masks for charging and discharging
    charge = df['power_actual'] > 0
    discharge = df['power_actual'] < 0

    df['power_output'] = -df['power_actual'].where(discharge, 0)
    df['power_input'] = df['power_actual'].where(charge, 0)
    df['power_target_output'] = -df['power_target'].where(discharge, 0)
    df['power_target_input'] = df['power_target'].where(charge, 0)
    df['power_actual_output'] = -df['power_actual'].where(discharge, 0)
    df['power_actual_input'] = df['power_actual'].where(charge, 0)

    df['massflow_output'] = -df['massflow_actual'].where(discharge, 0)
    df['massflow_input'] = df['massflow_actual'].where(charge, 0)
    df['total_mass'] = (df['massflow_input'] + df['massflow_output']).cumsum() * SEC2HOUR

    df['heat_discharge'] = df['heat'].where(discharge, 0)
    df['heat_charge'] = df['heat'].where(charge, 0)
    df['total_heat_discharge'] = df['heat_discharge'].cumsum()
    df['total_heat_charge'] = df['heat_charge'].cumsum()

    df['total_heat'] = df['heat'].cumsum()

    return df

def print_coupled_sim_rst(file_path, power_load_max, power_unload_max):
    ''' prints a summary of the results of a coupled simulation'''
    df = read_coupled_sim_rst(file_path)

    total_charging = len(df[df['power_actual'] > 0])
    total_discharging = len(df[df['power_actual'] < 0])
    energy_output_actual = round(df['power_output'].sum() * WH2GWH, 3)
    energy_input_actual = round(df['power_input'].sum() * WH2GWH, 3)
    total_heat_discharge = round(df['total_heat_discharge'].iloc[-1] * WH2GWH, 1)
    total_heat_charge = round(df['total_heat_charge'].iloc[-1] * WH2GWH, 1)
    heat_rate_min_charge = round(df['heat'].min() * W2MW, 1)
    heat_rate_max_discharge = round(df['heat'].max() * W2MW, 1)
    total_mass = round(df['total_mass'].iloc[-1], 5)
    total_mass_input = round(df['massflow_input'].cumsum().iloc[-1] * SEC2HOUR / 1e9, 3)
    total_mass_output = round(df['massflow_output'].cumsum().iloc[-1] * SEC2HOUR / 1e9, 3)
    volume_missmatch = round(df['massflow_output'].cumsum().iloc[-1] * SEC2HOUR / 1e9 +
                              df['massflow_input'].cumsum().iloc[-1] * SEC2HOUR / 1e9, 3)
    total_mass_min = round(df['total_mass'].cumsum().min() * SEC2HOUR / 1e9, 3)
    mass_flow_rate_max_discharge = round(df.loc[df['power_actual'] == power_load_max, 'massflow_actual'].max(), 1)
    mass_flow_rate_max_charge = round(df.loc[df['power_actual'] == power_unload_max, 'massflow_actual'].max(), 1)
    storage_pressure_end = round(df['storage_pressure'].iloc[-1], 3)
    storage_pressure_init = round(df['storage_pressure'].iloc[0], 1)
    storage_pressure_min = round(df['storage_pressure'].min(), 1)
    storage_pressure_max = round(df['storage_pressure'].max(), 1)

    # Create a DataFrame to store the summary statistics
    summary_stats = pd.DataFrame({
        'Results': [
            'Total charging [h]',
            'Total discharging [h]',
            'Energy output [GWh]',
            'Energy input [GWh]',
            'Total heat discharge [GWh]',
            'Total heat charge [GWh]',
            'Heat rate min(charge) [MW]',
            'Heat rate max(discharge) [MW]',
            'Total mass [Gt]',
            'Total mass input [Mt]',
            'Total mass output [Mt]',
            'Volume missmatch [Mt]',
            'Total mass min [Mt]',
            'Mass flow rate max discharge [kg/s]',
            'Mass flow rate max charge [kg/s]',
            'Storage pressure, end [bar]',
            'Storage pressure, initial [bar]',
            'Storage pressure min [bar]',
            'Storage pressure max [bar]'
        ],
        'Value': [
            total_charging,
            total_discharging,
            energy_output_actual,
            energy_input_actual,
            total_heat_discharge,
            total_heat_charge,
            heat_rate_min_charge,
            heat_rate_max_discharge,
            total_mass,
            total_mass_input,
            total_mass_output,
            volume_missmatch,
            total_mass_min,
            mass_flow_rate_max_discharge,
            mass_flow_rate_max_charge,
            storage_pressure_end,
            storage_pressure_init,
            storage_pressure_min,
            storage_pressure_max
        ]
    })

    print(tabulate(summary_stats, headers='keys', tablefmt='psql'))

def get_storage_efficiency(cycle_rst_path, plant_type):
    ''' get the storage efficiency for a given cycle result file based on ../fgasa/Integrated_CASE_Assessment/src/efficiency_calculation.py '''
    df = pd.read_csv(cycle_rst_path)
    df = df.loc[df['power_in'] != 0]

    if plant_type == 'diabatic':
        df['thermal_input_reference'] = df['thermal_input'] * df['reference_carnot_efficiency']
        df['storage_efficiency_min'] = (df['power_out'] - df['thermal_input_reference']) / df['power_in']
        df['storage_efficiency_pauschal'] = df['power_out'] / (df['power_in'] + df['thermal_input_reference'])
        df['reference_plant_efficiency_pauschal'] = df['storage_efficiency_pauschal'] * df['reference_carnot_efficiency']
    elif plant_type == 'adiabatic':
        df['storage_efficiency_min'] = df['power_out'] / df['power_in']
    else:
        raise ValueError(f"Invalid plant type: {plant_type}")

    return df

def get_proxy_model_domain_results(file_path, time):
    with open(file_path,'r') as file:
        lines = file.readlines()
        
    x_values = []
    y_values = []
    pressure_values = []

    target_line = f'STRANDID=1, SOLUTIONTIME={time}'
    start_index = None
   

    for i, line in enumerate(lines):
        if target_line in line:
            start_index = i + 1
        elif 'VARIABLES  = "X", "Y", "PRESSURE"' in line and start_index is not None:
            end_index = i
            break
        elif start_index is not None:
            values = line.strip().split('\t')
            x_values.append(float(values[0]))
            y_values.append(float(values[1]))
            pressure_values.append(float(values[2]))
    else:
        # If the target line or the data section is not found, return None
        return None

    df = pd.DataFrame({
        'X': x_values,
        'Y': y_values,
        'PRESSURE': pressure_values })

    return df

def get_proxy_model_tstep(lines):
    ''' extracts all the timesteps from domain results '''
    target_line = 'STRANDID=1, SOLUTIONTIME='
    timesteps = []

    for line in lines:
        if target_line in line:
            timestep = float(line.split(target_line)[1])
            timesteps.append(timestep)

    return np.array(timesteps)

def get_proxy_model_well_result(file_path):
    df = pd.read_csv(file_path,sep='\t',header=[0,1])
    df.columns = df.columns.map(lambda h: '{}_{}'.format(h[0], h[1]))
    return df

def write_fluid_pvtx(temperature, pressure, fluid, output_dir):
    ''' write fluid PVT data: Pressure must be in bar and Temperature in Celsius'''
    pressure = np.arange(pressure * 0.1, pressure * 3, 2) * 1e5  # in Pa for CP
    temperature = np.full_like(pressure, temperature + 273.15)  # in K

    # calculate fluid density and viscosity in cP
    fluid_density = CP.PropsSI('D', 'P', pressure, 'T', temperature, fluid)
    fluid_viscosity = CP.PropsSI('V', 'P', pressure, 'T', temperature, fluid) * 1e3

    data = np.column_stack((pressure / 1e5, temperature - 273.15, fluid_density, fluid_viscosity))

    header1 = ['# GAS_IDENT', fluid.strip(), '$ENTRIES', str(len(data)), '1\n']
    header2 = ['-- Pressure[bar] Temperature[°C] Density[kg/m³] Viscosity[cP or mPa*s]\n$DATA']
    header = '\n'.join(header1) + '\n'.join(header2)

    # write data to file
    filename = f'geostorage_{fluid}_CP.ptdv'
    output_path = os.path.join(output_dir, filename).upper()
    np.savetxt(output_path, data, delimiter='\t', header=header, fmt='%.4e', comments='', footer='#STOP')

    print(f' Msg: Fluid PVT is generated')
    return data

def resample_data_for_heatmap(temp_series):
    temp_np = temp_series.to_numpy()

    # define new data resolution
    num_hours = 24
    num_days = len(temp_np) // num_hours

    # Check that the data is long enough to reshape into a heatmap
    if len(temp_np) < num_days * num_hours:
        raise ValueError("Input data is too short to reshape into a heatmap")
    data_reshaped = temp_np[:num_days * num_hours]
    temp_heatmap = data_reshaped.reshape((num_days, num_hours))

    return temp_heatmap

def reshape_pressure_array(pressure_values, n):
        pressure_array = pressure_values.reshape(n, n)
        pressure_array = np.ma.masked_where(pressure_array < 0, pressure_array)
        
        return pressure_array