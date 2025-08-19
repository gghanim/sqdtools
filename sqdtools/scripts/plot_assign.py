from os import listdir as os_listdir, path as os_path
from starfile import read as starfile_read
import matplotlib.pyplot as plt
import pandas as pd
from itertools import cycle as itertools_cycle
import numpy as np
from re import search as re_search
import click
import concurrent.futures
import time

benchmark = False


def how_long(process: str, benchmark: bool):
    def decrator(func):
        # @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            total_time = end_time - start_time
            print(f"{process} took: \n --- {total_time:.4f} seconds ---\n")
            return result
        return wrapper
    return decrator if benchmark else lambda x: x


def get_file_paths(dir, suffix) -> list[str]:
    """
    Gets the most recent file with the suffix from the file path.
    """
    files = os_listdir(dir)
    filtered_paths = [file for file in files if file.endswith(suffix)]
    rel_filtered_paths = [os_path.join(dir, file) for file in filtered_paths]
    rel_filtered_paths.sort()
    return rel_filtered_paths


def get_column(file, from_table='model_classes', column='rlnClassDistribution') -> list:
    """ Gets reads and gets the specified column"""
    file_data = starfile_read(file, read_n_blocks=2)
    data = file_data[from_table][column].tolist()
    return data


@how_long("Usual DF", benchmark)
def merge_columns(file_paths, from_table='model_classes', column='rlnClassDistribution') -> pd.DataFrame:
    data = []
    for file in file_paths:
        row = get_column(file, from_table, column)
        data.append(row)
    df = pd.DataFrame(data)
    df.columns = [f'Class {i + 1}' for i in range(len(df.transpose()))]
    return df


@how_long("Concurrent DF", benchmark)
def concurrent_merge_columns(file_paths, from_table='model_classes', column='rlnClassDistribution', threads=None) -> pd.DataFrame:
    with concurrent.futures.ProcessPoolExecutor(threads) as exe:
        # futures = [exe.submit(process, file) for file in files]
        futures = exe.map(get_column, file_paths)
    df = pd.DataFrame(list(futures))
    df.columns = [f'Class {i + 1}' for i in range(len(df.transpose()))]
    return df


def get_max_iteration(file_list) -> str and int:
    n = re_search('it(.*)_model', file_list[-1]).group(1)  # Extracts value between 'it' & '_model'
    return n, int(n)


def dir_not_cleaned(file_list) -> bool:
    """ Compares two sets. One from number of files,
    the other from latest iteration number. """
    _, n = get_max_iteration(file_list)
    # Set from latest iteration number
    highest_iter_set = set(range(n + 1))
    # Set from number of files
    files_len_set = set(range(len(file_list)))
    return highest_iter_set == files_len_set


@click.command(no_args_is_help=True)
@click.argument('folder', type=click.Path(exists=True))
@click.option('--o', '--output', 'out', help="Optional name for the output file.", metavar='<output.pdf>')
@click.option('--ns', '--no_save', 'suppress_out', flag_value=True, help="Do not save the plot.")
@click.option('--b', '--benchmark', 'benchmark', flag_value=True, help="Do not save the plot.")
def cli(folder, out, suppress_out, benchmark):
    """
    Script for plotting 3D class asignments against iteration from RELIONs '_model.star' file.
    """

    job_number = os_path.basename(os_path.abspath(folder))
    data_column = 'rlnClassDistribution'  # Hard coded
    suffix = '_model.star'  # Hard coded

    # Get file list
    model_files = get_file_paths(folder, suffix)

    # # Get the data the usual way
    # df = merge_columns(model_files)
    # Get the data with concurrency, this is slightly faster
    df = concurrent_merge_columns(model_files, threads=5)

    # Prepare the plots and make them pretty.
    marker = itertools_cycle(('|', 'x', '*', 's', 'o', 'v'))
    for class_number in df:
        plt.plot(df[class_number], linewidth=0.75, marker=next(marker), markerfacecolor='none', markeredgewidth=0.75, markersize=4)
    plt.xlabel('Iteration')
    plt.ylabel(data_column)
    plt.xticks(np.arange(0, len(df), 5))
    plt.xlim(0, len(df) - 1)
    plt.legend([f'Class {i + 1}' for i in range(len(df))], loc='upper left', frameon=False, bbox_to_anchor=(1.00, 1))
    plt.title(f"3D Classification - {job_number}")
    plt.tight_layout(rect=[0, 0, 1, 1])

    # Set the output name if user does not provide value
    if not out:
        max_iteration, _ = get_max_iteration(model_files)
        out = f"3Dproportions_{job_number}_it{max_iteration}.pdf"

    # Check for cleaned directory to prevent overwriting
    if dir_not_cleaned(model_files) and not suppress_out:
        try:
            # histogrsam.figsize = (11.80, 8.85)
            # histogram.dpi = 300
            plt.savefig(out)
        except IOError:  # could also be IOError
            click.echo(f"  {click.style('WARNING:', fg='red', bold=True)} Did not save. Is this directory writable?")
        finally:
            plt.show()
    elif not dir_not_cleaned(model_files):
        click.echo(f"  {click.style('WARNING:', fg='red', bold=True)} Did not save. Intermediate files are missing. Did you gently clean this directory?")
        plt.show()
    else:
        plt.show()


if __name__ == '__main__':
    cli(max_content_width=120)
