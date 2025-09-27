# a python script to plot histograms of data, etc...
import starfile
import matplotlib.pyplot as plt
import numpy as np
import click
import ast
"""
To Do:
  1. Equalize the axes sharey=True
"""


def load_data(filename, data_column):
    star_df = starfile.read(filename)

    # check if the starfile is for micrographs, or particles, but not both
    match star_df:
        case {'particles': _, 'micrographs': _}:
            click.echo(f"  {click.style('ERROR:', fg='red', bold=True)} both 'micrographs' and 'particles' exist in this file.")
            exit()
        case {'micrographs': _}:
            star_file_type = 'micrographs'
        case {'particles': _}:
            star_file_type = 'particles'
        case _:
            click.echo(f"  {click.style('ERROR:', fg='red', bold=True)} unknown star file type.")
            exit()

    valid_data_columns = star_df[star_file_type].columns.tolist()

    # print the data columns in the star file and quit
    if data_column == "list":
        click.echo("\n  The following are valid data_column names:")
        for item in valid_data_columns:
            print(f"   {item}")
        exit()

    # catches bad column names
    elif data_column not in valid_data_columns:
        click.echo(f"  {click.style('ERROR:', fg='red', bold=True)} \"{data_column}\" is not a valid column name in \"{input.split('/')[-1]}\"")
        click.echo("\n  The following are valid data_column names:")
        for item in valid_data_columns:
            print(f"   {item}")
        exit()

    # make a dataframe of only what is needed
    if star_file_type == 'particles':
        data = star_df[star_file_type][['rlnClassNumber', data_column]]
    elif star_file_type == 'micrographs':
        data = star_df[star_file_type][[data_column]]

    return data, star_file_type


def fdb(data):
    # freedman_diaconis_bins
    # Calculate the IQR
    q25, q75 = np.percentile(data, [25, 75])
    iqr = q75 - q25
    if iqr == 0:
        iqr = 1
    # Calculate the bin width using the Freedman-Diaconis rule
    bin_width = 2 * iqr / np.cbrt(len(data))
    # Calculate the number of bins
    num_bins = int(np.ceil((max(data) - min(data)) / bin_width))
    return num_bins


def histogram_by_class(df, data_column, classes):
    bins = fdb(df[data_column])
    fig, axs = plt.subplots(len(classes), 1, sharex=True, sharey=False, tight_layout=True)

    # Deal with edge case of 1 class passed
    if len(classes) == 1:  # or not by_class:
        axs = [axs]

    for ax, class_number in zip(axs, classes):
        filter = df['rlnClassNumber'] == class_number
        class_data = df[filter][data_column]
        ax.hist(class_data, bins=bins, color='blue')
        ax.set_title(f'Class {class_number}: {data_column}')
    return fig


def histogram(df, data_column, classes):
    fig, ax = plt.subplots(1, 1, sharex=True, tight_layout=True)
    ax.hist(df[data_column], bins=fdb(df[data_column]), color='blue')

    # set tile and axis based on infered star_file_type
    ax.set_xlabel(f"{data_column}")
    if any(classes):
        ax.set_title(f"Class {', '.join(str(x) for x in classes)}: {data_column}")
        ax.set_ylabel("Number of particles")
    else:
        ax.set_ylabel("Number of micrographs")
    return fig


def validate_extension(path, extension):
    if path.endswith(extension):
        return path
    else:
        click.echo(f"  {click.style('ERROR:', fg='red', bold=True)} Wrong file format. \"{path}\" does not end with \"{extension}\".")
        raise ValueError()


@click.command(no_args_is_help=True)
@click.option('--i', '--input', 'input', required=True, type=click.Path(exists=True, resolve_path=False), help="Path to the input .star file", metavar='<starfile.star>')
@click.option('--data_column', 'data_column', default='rlnDefocusU', show_default=True, type=str, help="RELION data column to plot. \"list\" will print valid data column names.", metavar='<rlnDataColumn>')
@click.option('--by_class', is_flag=True, help="Split by class. Ignored for micrograph star files.")
@click.option('--c', '--classes', 'classes', type=str, help="Specify which class to plot. Pass a python list for multiple classes. Ignored for micrograph star files.", metavar='<class number>')
@click.option('--o', '--output', 'out', is_flag=False, flag_value="histogram_output.pdf", help="Optional name for the output file.", metavar='<output.pdf>')
def cli(input, data_column, classes, by_class, out):
    """
    Plots a histogram.
    Defaults to Defocus plots.
    """

    # Validate the inputs
    input = validate_extension(input, '.star')

    click.echo(f"  Reading \"{input.split('/')[-1]}\"...")  # Gets file name from the path
    data, star_file_type = load_data(input, data_column)

    # evaluates classes if particles
    if star_file_type == 'particles':
        if not classes:
            classes = data['rlnClassNumber'].unique()
        elif '[' in classes:
            classes = ast.literal_eval(classes)
        else:
            classes = [int(classes)]

        classes.sort()
        filter = data['rlnClassNumber'].isin(classes)
        data = data[filter]

    elif star_file_type == 'micrographs':
        classes = None
        by_class = None

    if by_class:
        click.echo("  Plotting data by class...")
        histogram_by_class(data, data_column, classes)
    else:
        click.echo("  Plotting data...")
        histogram(data, data_column, classes)

    if out:
        # histogram.figsize = (11.80, 8.85)
        # histogram.dpi = 300
        plt.savefig(out)
        plt.show()
    else:
        plt.show()
        exit()


if __name__ == '__main__':
    cli(max_content_width=120)
