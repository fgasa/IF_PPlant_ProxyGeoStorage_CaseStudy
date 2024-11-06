import os
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator
import utilities as util

W2MW = 1e-6
SEC2HOUR = 3600
SEC2DAY = 86400
COLORS = {
        'target_power': 'tab:red',
        'actual_power': 'tab:blue',
        'pressure': 'black',
        'charging': 'tab:blue',
        'discharging': 'tab:green',
        'storage_level': 'tab:purple'
    }

def plot_heatplot(path, output_dir):
    scenario_name = os.path.basename(path)
    df = util.read_coupled_sim_rst(path)
    fig, ax1 = plt.subplots(figsize=(6, 5))

    power_actual = df['power_actual'] * W2MW
    power_actual_map = util.resample_data_for_heatmap(power_actual)
    heatmap1 = ax1.imshow(power_actual_map, cmap='bwr', aspect='auto')

    for ax in fig.get_axes():
        ax.xaxis.set_minor_locator(AutoMinorLocator(2))
        ax.yaxis.set_minor_locator(AutoMinorLocator(2))
        ax.xaxis.set_major_locator(plt.MaxNLocator(6))
        ax.yaxis.set_major_locator(plt.MaxNLocator(10))
        ax.grid(False)
        ax.set(xlabel='Hours', ylabel='Days',xlim=(0, None))

    cbar = plt.colorbar(heatmap1, fraction=0.02, pad=0.05)
    cbar.locator = plt.MaxNLocator(6)
    cbar.outline.set_edgecolor('black')
    cbar.dividers.set_color('black')

    fig_ext = ['png','pdf']
    for ext in fig_ext:
        figure_name = '{}/Heatmap_' + scenario_name +  '.' + ext
        fig.savefig(figure_name.format(output_dir), dpi=200, bbox_inches='tight',transparent=True)

def plot_scenario_rst(path, output_dir):
    ''' plot power, pressure, mass flow rate, and storage level for a given scenario '''

    df = util.read_coupled_sim_rst(path)
    time = df.index
    scenario = os.path.basename(path)

    power_target = df['power_target'] * W2MW
    power_actual = df['power_actual'] * W2MW
    pressure = df['storage_pressure']
    mfr_input = df['massflow_input']
    mfr_output = df['massflow_output']
    gip = df['total_mass'] / 1000000  # ton

    limits = {
        'power_min': power_target.min() * 1.5,
        'power_max': power_target.max() * 1.5,
        'pressure_min': pressure.min() * 0.8,
        'pressure_max': pressure.max() * 1.2,
        'mfr_min': mfr_output.min() * 1.5,
        'mfr_max': mfr_input.max() * 1.2,
        'level_min': gip.min() * 1.5,
        'level_max': gip.max() * 1.5,
        'time_min': 0,
        'time_max': time.max()
    }


    fig, (ax1, ax3) = plt.subplots(1, 2, figsize=(16, 4.5))
    ax11 = ax1.twinx()  # pressure
    ax33 = ax3.twinx()  # gip

    ax1.plot(time, power_target, label='Target Power', markersize=2, marker='s', mec=COLORS['target_power'], color='gray', mfc=COLORS['target_power'], lw=0.1, ls='-')
    ax1.plot(time, power_actual, label='Actual Power', markersize=1.2, marker='>', color=COLORS['actual_power'], lw=2, ls='None')
    ax1.plot([], [], label='Pressure', lw=0.5, color=COLORS['pressure'])
    ax11.plot(time, pressure, color=COLORS['pressure'], lw=1)
    ax3.plot(time, mfr_input, label='Charging', markersize=2, marker='^', color=COLORS['charging'], lw=0.05)
    ax3.plot(time, mfr_output, label='Discharging', markersize=2, marker='v', color=COLORS['discharging'], lw=0.05)
    ax33.plot(time, gip, color='gray')
    ax1.plot([], [], label='Charging', markersize=2, marker='^', color=COLORS['charging'], lw=0.05)
    ax1.plot([], [], label='Discharging', markersize=2, marker='v', color=COLORS['discharging'], lw=0.05)
    ax1.plot([], [], label='Storage level', lw=2, color=COLORS['storage_level'])

    for ax in fig.get_axes():
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(True)
        ax.xaxis.set_minor_locator(AutoMinorLocator(2))
        ax.yaxis.set_minor_locator(AutoMinorLocator(2))
        ax.set(ylabel='Power in MW', xlim=(limits['time_min'], limits['time_max']), ylim=(limits['power_min'], limits['power_max']))
        ax.grid(False)
        ax.set_xlabel('Time in hours')

    ax11.spines['right'].set_color(COLORS['pressure'])
    ax11.set(ylim=(limits['pressure_min'], limits['pressure_max']))
    ax11.set_ylabel('Pressure in bar', color=COLORS['pressure'])
    ax11.tick_params(direction='out', which='minor', colors=COLORS['pressure'])
    ax11.grid(False)

    ax3.set(ylabel='Mass flow rate in kg/s', xlim=(limits['time_min'], limits['time_max']), ylim=(limits['mfr_min'], limits['mfr_max']))
    ax33.spines['right'].set_color(COLORS['storage_level'])
    ax33.set(xlim=(limits['time_min'], limits['time_max']), ylim=(limits['level_min'], limits['level_max']))
    ax33.set_ylabel('Storage level in kt', color=COLORS['storage_level'])
    ax33.tick_params(direction='out', which='minor', colors=COLORS['storage_level'])

    legend1 = ax1.legend(loc='lower center', bbox_to_anchor=(1.2, -0.4), borderaxespad=0.2, markerscale=6., ncol=6, labelspacing=0.2, frameon=False, borderpad=0.4)
    for line1 in legend1.get_lines():
        line1.set_linewidth(4.0)

    fig.subplots_adjust(wspace=0.2)
    fig_ext = ['png', 'pdf']
    for ext in fig_ext:
        figure_name = f'{output_dir}/Fig_{scenario}.{ext}'
        fig.savefig(figure_name, dpi=200, transparent=False)
    print(f'Figure name: {figure_name}')

def plot_pressure_map(df, time, output_dir):
    fig, ax1 = plt.subplots(figsize=(6, 6))
    x_values = df['X'].values
    y_values = df['Y'].values
    pressure_values = df['PRESSURE'].values
    #print(' Msg: Pressure max and min ', df['PRESSURE'].max(), '   ', df['PRESSURE'].min())
    n = int(len(pressure_values)**0.5)
    pressure_array = util.reshape_pressure_array(pressure_values, n)

    contourf_map = ax1.contourf(x_values.reshape(n, n), y_values.reshape(n, n), pressure_array, cmap="gray")

            
    cbar = fig.colorbar(contourf_map, orientation='vertical', ax=ax1, shrink=1, fraction=0.04, pad=0.04)
    cbar.minorticks_off()
    cbar.ax.set_ylabel('Pressure [bar]')

    ax1.set(xlabel='X [m]', ylabel='Y [m]')
    ax1.set_aspect('equal')
    ax1.grid(False)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.xaxis.set_minor_locator(AutoMinorLocator(1))
    ax1.yaxis.set_minor_locator(AutoMinorLocator(1))
    ax1.tick_params(direction='out', colors='black')
    ax1.xaxis.set_major_locator(plt.MaxNLocator(5))
    ax1.yaxis.set_major_locator(plt.MaxNLocator(5))
    ax1.spines['bottom'].set_position(('outward', 10))
    ax1.spines['left'].set_position(('outward', 10))

    plt.tight_layout(pad=0.001)
    time = float(time)/SEC2DAY

    fig_ext = ['png', 'pdf']
    for ext in fig_ext:
        figure_name = f'{output_dir}/Fig_Pressure_Map_{time}.{ext}'
        fig.savefig(figure_name, dpi=200, bbox_inches="tight", transparent=False)
    print(f'Figure name: {figure_name}')
    plt.show()
    plt.clf()