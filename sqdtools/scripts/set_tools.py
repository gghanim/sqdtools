import numpy as np
import click
from starfile_rs import read_star
import starfile
import pandas as pd

def write_unique(df_type, label, unique_df, file_df):
    if df_type == 'list':
        click.echo(f'    File {label} is not the usual RELION STAR format. Skipping...')
    elif len(unique_df) == 0:
        click.echo(f'    No unique entries to file {label}. Skipping...')
    else:
        unique_starfile = {
        'optics' : file_df['optics'],
        df_type: unique_dt}
        starfile.write(unique_starfile, "{label}_unique.star")
        click.echo(f'    Wrote {label} unique to \"{label}_unique.star\".')

def validate_extension(path, extension):
    if path.endswith(extension):
        return path
    else:
        click.echo(f"  {click.style('ERROR:', fg='red', bold=True)} Wrong file format. \"{path}\" does not end with \"{extension}\".")
        raise ValueError()

def write_intersect(df_type, label, other_label, intersect_df, unique_df, file_df):
    if df_type == 'items':
        click.echo(f'\n    File {label} is not the usual RELION STAR format. Skipping...')
    else:
        intersect_label = f"{label}n{other_label}"
        if len(intersect_df) == 0:
            click.echo(f'\n      {len(intersect_df):,} particles in {label} intersect {other_label}. Skipping writing...')
        else:
            intersect_starfile = {
            'optics' : file_df['optics'],
            df_type: intersect_df}
            starfile.write(intersect_starfile, f"{intersect_label}_keeping{label}.star")
            click.echo(f'\n    Wrote {label} intersect {other_label} (keeping {label}) to \"{intersect_label}_keeping{label}.star\".')
            click.echo(f'      {len(intersect_df):,} particles in {label} intersect {other_label}.')

        if len(unique_df) == 0:
            click.echo(f'\n      {len(unique_df):,} particles in {label} unique. Skipping writing...')
        else:
            unique_starfile = {
            'optics' : file_df['optics'],
            df_type: unique_df}
            starfile.write(unique_starfile, f"{label}_unique.star")
            click.echo(f'    Wrote {label} unique to \"{label}_unique.star\".')
            click.echo(f'      {len(unique_df):,} particles in {label} unique.')


@click.command(no_args_is_help=True)
@click.option('--a', '--input_a', 'input_file_a', required=True, type=click.Path(exists=True, resolve_path=False), help="Path to input .star file A.", metavar='<starfile_A.star>')
@click.option('--b', '--input_b', 'input_file_b', required=True, type=click.Path(exists=True, resolve_path=False), help="Path to input .star file B.", metavar='<starfile_B.star>')
@click.option('--n', '--intersect', 'operation', flag_value='intersect', default=True, help="Intesect file A with file B. Four files will be written. AnB(keeping A).star, A_unique.star, BnA(keeping B).star, and B_unique.star.")
@click.option('--u', '--unique', 'operation', flag_value='unique', help="operation xyz")
@click.option('--data_column', 'data_column', multiple=True, required=True, type=str, help="RELION data column to select. \"list\" will print valid data column names.", metavar='<rlnDataColumn>')
#@click.option('--o', '--output', 'out', is_flag=False, flag_value=None, help="Optional name to add for the output files.", metavar='<output_starfile.star>')


def cli(input_file_a, input_file_b, operation, data_column):
    
    # Read file A
    validate_extension(input_file_a, '.star')
    star_a = starfile.read(input_file_a)
    
    # Read file B
    validate_extension(input_file_b, '.star')
    star_b = starfile.read(input_file_b)

    # Read files
    if isinstance(star_a, pd.DataFrame):
        dfA, A_type = star_a, 'items'
    elif isinstance(star_a, dict):
        if 'micrographs' in star_a.keys():
            dfA, A_type = star_a['micrographs'], 'micrographs'
        elif 'particles' in star_a.keys():
            dfA, A_type = star_a['particles'], 'particles'

    if isinstance(star_b, pd.DataFrame):
        dfB, B_type = star_b, 'items'
    elif isinstance(star_b, dict):
        if 'micrographs' in star_b.keys():
            dfB, B_type = star_b['micrographs'], 'micrographs'
        elif 'particles' in star_b.keys():
            dfB, B_type = star_b['particles'], 'particles'
    
    # Check data columns
    data_columns = list(set(data_column))
    if "list" in data_columns:
        valid_data_columns_A = dfA.columns.tolist()
        valid_data_columns_B = dfB.columns.tolist()
        valid_data_columns = list(set(valid_data_columns_A) & set(valid_data_columns_B))
        click.echo("\n  The following are valid data_column names in file A and in file B:")
        for item in valid_data_columns:
            print(f"    {item}")
        exit()

    click.echo(f"  Reading \"{input_file_a}\" as file A.")
    click.echo(f"  Reading \"{input_file_b}\" as file B.")
    click.echo(f'    {len(dfA):,} {A_type} in file A.')
    click.echo(f'    {len(dfB):,} {B_type} in file B.')

    if operation == 'intersect':
        click.echo(f'\n  Intersecting files on {", ".join(f'"{x}"' for x in data_columns)}...')

        # Take A intersection with B
        AnB = dfA.merge(dfB[data_columns], on=data_columns, how="inner")
        A_unique = (dfA.merge(dfB[data_columns], on=data_columns, how="left", indicator=True)
                   .query('_merge == "left_only"')
                   .drop(columns="_merge"))
        # Take B intersection with A
        BnA = dfB.merge(dfA[data_columns], on=data_columns, how="inner")
        B_unique = (dfB.merge(dfA[data_columns], on=data_columns, how="left", indicator=True)
           .query('_merge == "left_only"')
           .drop(columns="_merge"))

        write_intersect(A_type, "A", "B", AnB, A_unique, star_a)
        write_intersect(B_type, "B", "A", BnA, B_unique, star_b)

    if operation == 'unique':
        click.echo(f'\n  Taking unique entries on {", ".join(f'"{x}"' for x in data_columns)}...')

        # Taking unique A
        A_unique = (dfA.merge(dfB[data_columns], on=data_columns, how="left", indicator=True)
                    .query('_merge == "left_only"')
                    .drop(columns="_merge"))

        # Taking unique B
        B_unique = (dfB.merge(dfA[data_columns], on=data_columns, how="left", indicator=True)
                    .query('_merge == "left_only"')
                    .drop(columns="_merge"))

        write_unique(A_type, 'A', A_unique, star_a)
        write_unique(B_type, 'B', B_unique, star_b)


if __name__ == '__main__':
    cli(max_content_width=120)
