# a python script to plot histograms of defocus, etc...
import starfile
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
# from colorama import Fore, Style, init
import click
from os import listdir as os_listdir, path as os_path
import ast
"""
To Do:
  1. Equalize the axes sharey=True
  2. Add title
  3. Read healpix order from *_optimiser.star to adjust gridsize
    a. for healpix 2 grid size of 25 is good (0=30, 1=15, 2=7.5)
"""

# Initialize colorama
# init()


def load_data(filename, data_column_x, data_column_y):
    star_df = starfile.read(filename)

    valid_data_columns = star_df['particles'].columns.tolist()

    # print the data columns in the star file and quit
    if data_column_x == "list" or data_column_y == "list":
        click.echo("\n  The following are valid \"x\" and \"y\" data_column names:")
        for item in valid_data_columns:
            print(f"   {item}")
        exit()

    # catches bad column names
    elif data_column_x not in valid_data_columns or data_column_x not in valid_data_columns:
        click.echo(f"  {click.style('ERROR:', fg='red', bold=True)} \"{data_column_x}\" is not a valid column name in \"{input.split('/')[-1]}\"")
        click.echo("\n  The following are valid \"x\" and \"y\" data_column names:")
        for item in valid_data_columns:
            print(f"   {item}")
        exit()

    data = star_df['particles'][['rlnClassNumber', data_column_x, data_column_y]]
    # try:
    #     read from micrographs
    return data


def histogram2d_by_class(df, data_column_x, data_column_y, gridsize, classes):
    fig, axs = plt.subplots(len(classes), 1, sharex=True, sharey=True, tight_layout=True)

    # Deal with edge case of 1 class passed
    if len(classes) == 1:  # or not by_class: 
        axs = [axs]

    # Plot a histogram for each class
    for ax, class_number in zip(axs, classes):
        filter = df['rlnClassNumber'] == class_number
        class_data = df[filter]
        hb = ax.hexbin(class_data[data_column_x], class_data[data_column_y], bins='log', gridsize=gridsize)
        ax.set_title(f'Class {class_number}: {data_column_x} vs. {data_column_y}')
        divider = make_axes_locatable(ax)
        cax = divider.append_axes('right', size='5%', pad=0.1)
        cb = fig.colorbar(hb, ax=ax, cax=cax)
        cb.set_label('Particles')
    return fig


def histogram2d(df, data_column_x, data_column_y, gridsize, classes):
    fig, ax = plt.subplots(1, 1, sharex=True, tight_layout=True)
    hb = ax.hexbin(df[data_column_x], df[data_column_y], bins='log', gridsize=gridsize)  # cmap=colormap, gridsize=gridsize)
    ax.set_title(f"Class {', '.join(str(x) for x in classes)}: {data_column_x} vs. {data_column_y}")
    ax.set_xlabel(data_column_x)
    ax.set_ylabel(data_column_y)
    # fig.gca().set_aspect('equal', adjustable='box')
    divider = make_axes_locatable(ax)
    cax = divider.append_axes('right', size='5%', pad=0.1)
    cb = fig.colorbar(hb, ax=ax, cax=cax)
    cb.set_label('Particles')
    return fig


def get_file_paths(dir, suffix) -> list[str]:
    """
    Gets the most recent file with the suffix from the file path.
    """
    dir = os_path.dirname(os_path.abspath(dir))  # gets parent directory
    files = os_listdir(dir)
    filtered_paths = [file for file in files if file.endswith(suffix)]
    rel_filtered_paths = [os_path.join(dir, file) for file in filtered_paths]
    rel_filtered_paths.sort()
    return rel_filtered_paths


def validate_extension(path, extension):
    if path.endswith(extension):

        return path

    else:
        click.echo(f"  {click.style('ERROR:', fg='red', bold=True)} Wrong file format. \"{path}\" does not end with \"{extension}\".")

        raise ValueError()


@click.command(no_args_is_help=True)
@click.option('--i', '--input', 'input', required=True, type=click.Path(exists=True, resolve_path=False), help="Path to the input .star file", metavar='<starfile.star>')
@click.option('--x', '--data_x', 'data_column_x', default='rlnAngleRot', show_default=True, type=str, help="RELION data column to plot on x. \"list\" will print valid data column names.", metavar='<rlnDataColumn>')
@click.option('--y', '--data_y', 'data_column_y', default='rlnAngleTilt', show_default=True, type=str, help="RELION data column to plot on y. \"list\" will print valid data column names.", metavar='<rlnDataColumn>')
@click.option('--by_class', is_flag=True, help="Split by class.")
@click.option('--c', '--classes', 'classes', type=str, help="Specify which class to plot. Pass a python list for multiple classes.", metavar='<class number>')
@click.option('--o', '--output', 'out', is_flag=False, flag_value="histogram_output.pdf", help="Optional name for the output file.", metavar='<output.pdf>')
def cli(input, data_column_x, data_column_y, classes, by_class, out):
    """
    Plots a 2D histogram.
    Defaults to Euler Angles Orientation plots.
    """

    # Validate the inputs
    input = validate_extension(input, '.star')

    # try to automatically set the gridsize
    model_files = get_file_paths(input, "_optimiser.star")
    model_file = model_files[-1]  # gets latest file
    try:
        with open(model_file, 'r') as file:
            for line in file:
                if '--healpix_order' in line:
                    # Assuming the line has the format "--healpix_order <value>"
                    parts = line.strip().split()
                    if '--healpix_order' in parts:
                        index = parts.index('--healpix_order')
                        # The value should be the next item in the list
                        if index + 1 < len(parts):
                            healpix_order = int(parts[index + 1])
                        break
        if healpix_order <= 2:
            gridsize = 25
        else:
            gridsize = 50
    except:
        gridsize = 50

    click.echo(f"  Reading \"{input.split('/')[-1]}\"...")  # Gets file name from the path
    data = load_data(input, data_column_x, data_column_y)

    # Allows sorting by classes
    if not classes:  # Get all classes if not specified
        classes = data['rlnClassNumber'].unique()
    elif '[' in classes:  # Checks for a list of classes
        classes = ast.literal_eval(classes)
    else:
        classes = [int(classes)]

    # Filter the classes
    classes.sort()
    filter = data['rlnClassNumber'].isin(classes)
    data = data[filter]

    if by_class:
        click.echo("  Plotting data by class...")
        histogram2d_by_class(data, data_column_x, data_column_y, gridsize, classes)
    else:
        click.echo("  Plotting data.")
        histogram2d(data, data_column_x, data_column_y, gridsize, classes)

    # Save if out specified, else plot
    if out:
        # histogram.figsize = (11.80, 8.85)
        # histogram.dpi = 300
        plt.savefig(out)
        plt.show()
    else:
        plt.show()
        click.echo("  Plot not saved.")


if __name__ == '__main__':
    cli(max_content_width=120)
