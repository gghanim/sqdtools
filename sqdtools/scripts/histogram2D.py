# a python script to plot histograms of defocus, etc...
#import starfile
from starfile_rs import read_star
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import click
from os import listdir as os_listdir, path as os_path
import ast
import time
import functools


"""
To Do:
  3. expand to micrographs

  1. Equalize the axes sharey=True
  2. Add title
  3. Read healpix order from *_optimiser.star to adjust gridsize
    a. for healpix 2 grid size of 25 is good (0=30, 1=15, 2=7.5)
"""

def timer(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        print(f"    {func.__name__} took {end - start:.4f} seconds")
        return result
    return wrapper

# @timer
# def load_data(filename, data_column_x, data_column_y):
#     click.echo(f"  Reading \"{filename.split('/')[-1]}\"...")  # Gets file name from the path
#     star_df = starfile.read(filename)

#     valid_data_columns = star_df['particles'].columns.tolist()

#     # print the data columns in the star file and quit
#     if data_column_x == "list" or data_column_y == "list":
#         click.echo("\n  The following are valid \"x\" and \"y\" data_column names:")
#         for item in valid_data_columns:
#             print(f"   {item}")
#         exit()

#     # catches bad column names
#     elif data_column_x not in valid_data_columns or data_column_x not in valid_data_columns:
#         click.echo(f"  {click.style('ERROR:', fg='red', bold=True)} \"{data_column_x}\" is not a valid column name in \"{input_file.split('/')[-1]}\"")
#         click.echo("\n  The following are valid \"x\" and \"y\" data_column names:")
#         for item in valid_data_columns:
#             print(f"   {item}")
#         exit()

#     data = star_df['particles'][['rlnClassNumber', data_column_x, data_column_y]]
#     # try:
#     #     read from micrographs
#     return data

@timer
def load_data(filename, data_column_x, data_column_y):
    click.echo(f"  Reading \"{filename.split('/')[-1]}\"...")

    star_df = read_star(filename)

    # check if the starfile is for micrographs, or particles, but not both
    match star_df:
        case {'particles': _, 'micrographs': _}:
            click.echo(f"  {click.style('ERROR:', fg='red', bold=True)} both 'micrographs' and 'particles' exist in this file.")
            exit()
        case {'micrographs': _}:
            star_file_type = 'micrographs'
            if data_column_x == None: data_column_x = 'rlnCtfIceRingDensity'
            if data_column_y == None: data_column_y = 'rlnCtfMaxResolution'
        case {'particles': _}:
            star_file_type = 'particles'
            if data_column_x == None: data_column_x = 'rlnAngleRot'
            if data_column_y == None: data_column_y = 'rlnAngleTilt'
        case _:
            click.echo(f"  {click.style('ERROR:', fg='red', bold=True)} unknown star file type.")
            exit()

    star_df = star_df[star_file_type].to_pandas()
    valid_data_columns = star_df.columns.tolist()

    # print the data columns in the star file and quit
    if data_column_x == "list" or data_column_y == "list":
        click.echo("\n  The following are valid \"x\" and \"y\" data_column names:")
        for item in valid_data_columns:
            print(f"   {item}")
        exit()

    # catches bad column names
    elif data_column_x not in valid_data_columns or data_column_x not in valid_data_columns:
        click.echo(f"  {click.style('ERROR:', fg='red', bold=True)} \"{data_column_x}\" is not a valid column name in \"{filename.split('/')[-1]}\"")
        click.echo("\n  The following are valid \"x\" and \"y\" data_column names:")
        for item in valid_data_columns:
            print(f"   {item}")
        exit()

    # make a dataframe of only what is needed
    if star_file_type == 'particles':
        data = star_df[['rlnClassNumber', data_column_x, data_column_y]]
    elif star_file_type == 'micrographs':
        data = star_df[[data_column_x, data_column_y]]

    return data, star_file_type, data_column_x, data_column_y


def histogram2d(df, data_column_x, data_column_y, gridsize, classes, star_file_type):
    fig, ax = plt.subplots(1, 1, sharex=True, tight_layout=True)
    hb = ax.hexbin(df[data_column_x], df[data_column_y], bins='log', gridsize=gridsize)

    if classes is not None:
        ax.set_title(f"Class {', '.join(str(x) for x in classes)}: {data_column_x} vs. {data_column_y}")
    ax.set_xlabel(data_column_x)
    ax.set_ylabel(data_column_y)

    divider = make_axes_locatable(ax)
    cax = divider.append_axes('right', size='5%', pad=0.1)
    cb = fig.colorbar(hb, ax=ax, cax=cax)
    cb.set_label('Particles')

    if star_file_type == 'particles':
        cb.set_label('Particles')
    elif star_file_type == 'micrographs':
        cb.set_label('Micrographs')

    return fig


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
@click.option('--i', '--input', 'input_file', required=True, type=click.Path(exists=True, resolve_path=False), help="Path to the input .star file", metavar='<starfile.star>')
@click.option('--x', '--data_x', 'data_column_x', show_default=False, type=str, help="RELION data column to plot on x. Default is 'rlnAngleRot' (particles) or 'rlnCtfIceRingDensity' (micrographs). \"list\" will print valid data column names.", metavar='<rlnDataColumn>')
@click.option('--y', '--data_y', 'data_column_y', show_default=False, type=str, help="RELION data column to plot on y. Default is 'rlnAngleTilt' (particles) or 'rlnCtfMaxResolution' (micrographs). \"list\" will print valid data column names.", metavar='<rlnDataColumn>')
@click.option('--by_class', is_flag=True, help="Split by class.")
@click.option('--c', '--classes', 'classes', multiple=True, help="Specify which class to plot. You can specify multiple. Ignored for micrograph star files.", metavar='<class number>')
@click.option('--o', '--output', 'out', is_flag=False, flag_value="histogram_output.pdf", help="Optional name for the output file.", metavar='<output.pdf>')
def cli(input_file, data_column_x, data_column_y, classes, by_class, out):
    """
    Plots a 2D histogram.
    Defaults to Euler Angles Orientation plots.
    """

    # Validate the inputs
    input_file = validate_extension(input_file, '.star')
    print(type(classes))
    # try to automatically set the gridsize
    try:
        model_files = get_file_paths(input_file, "_optimiser.star")
        model_file = model_files[-1]  # gets latest file
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

    #data = load_data(input_file, data_column_x, data_column_y)
    data, star_file_type, data_column_x, data_column_y = load_data(input_file, data_column_x, data_column_y)

    # evaluates classes if particles
    if star_file_type == 'particles':
        if not classes:
            classes = data['rlnClassNumber'].unique()
            print(f"Not classes {classes}")
        else:
            classes = [ int(n) for n in classes]


        # Filter the classes
        classes.sort()
        filter = data['rlnClassNumber'].isin(classes)
        data = data[filter]

    elif star_file_type == 'micrographs':
        classes = None
        by_class = None

    if by_class:
        click.echo("  Plotting data by class...")
        histogram2d_by_class(data, data_column_x, data_column_y, gridsize, classes)
    else:
        click.echo("  Plotting data.")
        histogram2d(data, data_column_x, data_column_y, gridsize, classes, star_file_type)

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
