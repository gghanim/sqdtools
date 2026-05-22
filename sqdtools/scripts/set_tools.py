import numpy as np
import click
from starfile_rs import read_star
import starfile
import pandas as pd


def load_data(filename, data_column=None):
    star_df = read_star(filename)

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

    optics = star_df['optics'].to_pandas()
    star_df = star_df[star_file_type].to_pandas()
    valid_data_columns = star_df.columns.tolist()

    # print the data columns in the star file and quit
    if data_column is None:
        pass

    elif data_column == "list":
        click.echo("\n  The following are valid data_column names:")
        for item in valid_data_columns:
            print(f"   {item}")
        exit()

    # catches bad column names
    elif data_column not in valid_data_columns:
        click.echo(f"  {click.style('ERROR:', fg='red', bold=True)} \"{data_column}\" is not a valid column name in \"{filename.split('/')[-1]}\"")
        click.echo("\n  The following are valid data_column names:")
        for item in valid_data_columns:
            print(f"   {item}")
        exit()

    return optics, star_df, star_file_type


def validate_extension(path, extension):
    if path.endswith(extension):
        return path
    else:
        click.echo(f"  {click.style('ERROR:', fg='red', bold=True)} Wrong file format. \"{path}\" does not end with \"{extension}\".")
        raise ValueError()


def unique():
    pass


@click.command(no_args_is_help=True)
@click.option('--i', '--input', 'input_file', multiple=True, required=True, type=click.Path(exists=True, resolve_path=False), help="Path to the input .star file", metavar='<starfile.star>')
@click.option('--u', '--unique', 'operation', flag_value='unique', default=True)
@click.option('--n', '--intersect', 'operation', flag_value='intersect')
#@click.option('--data_column', 'data_column', default='rlnDefocusU', show_default=True, type=str, help="RELION data column to select. \"list\" will print valid data column names.", metavar='<rlnDataColumn>')
#@click.option('--o', '--output', 'out', is_flag=False, flag_value="histogram_output.pdf", help="Optional name for the output file.", metavar='<output.pdf>')
def cli(input_file, operation):

    file_list = []
    for file in input_file:
        click.echo(f"  Reading \"{file}\".")
        star = starfile.read(file)
        file_list.append(star)

    if operation == 'unique':
        if (length := len(input_file)) > 1:
            click.echo(f"\n  Merging starfiles.")
            merged = {}
            for data in file_list:
                    for key, df in data.items():
                        if key in merged:
                            merged[key] = pd.concat([merged[key], df], ignore_index=True)
                        else:
                            merged[key] = df.copy()
        else:
            merged = file_list[0]

        total_particles = len(merged['particles'])
        click.echo(f'    {total_particles:,} total particles.')

        # Drop duplicates
        for key in merged:
            if key == 'optics':
                merged[key] = merged[key].drop_duplicates(subset='rlnOpticsGroupName')
            if key == 'particles':
                merged[key] = merged[key].drop_duplicates(subset='rlnImageName')

        unique_particles = len(merged['particles'])
        click.echo(f'    {total_particles-unique_particles:,} duplicate particles.')
        click.echo(f'    {unique_particles:,} unique particles.')

        click.echo(f'\n  Wrote {unique_particles:,} particles to \"unique.star\".')
        starfile.write(merged, "unique.star")

    if operation == 'intersect':
        if len(file_list) > 2:
            click.echo(f"  {click.style('ERROR:', fg='red', bold=True)} Intersection only works with 2 files...")
            raise ValueError()

        click.echo(f'\n  Intersecting files...')
        click.echo(f'    \"{input_file[0]}\" is file A.')
        click.echo(f'    \"{input_file[1]}\" is file B.')
        dfA, dfB = file_list[0]['particles'], file_list[1]['particles']

        click.echo(f'\n    {len(dfA):,} particles in A.')
        click.echo(f'    {len(dfB):,} particles in B.')

        AnB = dfA[dfA['rlnImageName'].isin(dfB['rlnImageName'])]
        AnB_starfile = {
        'optics' : file_list[0]['optics'],
        'particles': AnB
        }
        starfile.write(AnB_starfile, "AnB_keepingA.star")
        click.echo(f'    {len(AnB):,} particles in A intersect B.')

        BnA = dfB[dfB['rlnImageName'].isin(dfA['rlnImageName'])]
        BnA_starfile = {
        'optics' : file_list[1]['optics'],
        'particles': BnA
        }
        starfile.write(BnA_starfile, "AnB_keepingB.star")

        click.echo(f'\n  Wrote A intersect B (keeping A) to \"AnB_keepingA.star\".')
        click.echo(f'  Wrote A intersect B (keeping B) to \"AnB_keepingB.star\".')
if __name__ == '__main__':
    cli(max_content_width=120)
