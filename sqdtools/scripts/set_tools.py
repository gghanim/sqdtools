import numpy as np
import click
from starfile_rs import read_star
import starfile
import pandas as pd


# def load_data(filename, data_column=None):
#     star_df = read_star(filename)

#     # check if the starfile is for micrographs, or particles, but not both
#     match star_df:
#         case {'particles': _, 'micrographs': _}:
#             click.echo(f"  {click.style('ERROR:', fg='red', bold=True)} both 'micrographs' and 'particles' exist in this file.")
#             exit()
#         case {'micrographs': _}:
#             star_file_type = 'micrographs'
#         case {'particles': _}:
#             star_file_type = 'particles'
#         case _:
#             click.echo(f"  {click.style('ERROR:', fg='red', bold=True)} unknown star file type.")
#             exit()

#     optics = star_df['optics'].to_pandas()
#     star_df = star_df[star_file_type].to_pandas()
#     valid_data_columns = star_df.columns.tolist()

#     # print the data columns in the star file and quit
#     if data_column is None:
#         pass

#     elif data_column == "list":
#         click.echo("\n  The following are valid data_column names:")
#         for item in valid_data_columns:
#             print(f"   {item}")
#         exit()

#     # catches bad column names
#     elif data_column not in valid_data_columns:
#         click.echo(f"  {click.style('ERROR:', fg='red', bold=True)} \"{data_column}\" is not a valid column name in \"{filename.split('/')[-1]}\"")
#         click.echo("\n  The following are valid data_column names:")
#         for item in valid_data_columns:
#             print(f"   {item}")
#         exit()

#     return optics, star_df, star_file_type


def validate_extension(path, extension):
    if path.endswith(extension):
        return path
    else:
        click.echo(f"  {click.style('ERROR:', fg='red', bold=True)} Wrong file format. \"{path}\" does not end with \"{extension}\".")
        raise ValueError()


@click.command(no_args_is_help=True)
@click.option('--i', '--input', 'input_file', multiple=True, required=True, type=click.Path(exists=True, resolve_path=False), help="Path to the input .star file", metavar='<starfile.star>')
@click.option('--u', '--unique', 'operation', flag_value='unique', default=True, help="operation xyz")
@click.option('--n', '--intersect', 'operation', flag_value='intersect', help="operation xyz")
@click.option('--data_column', 'data_column', multiple=True, required=True, type=str, help="RELION data column to select. \"list\" will print valid data column names.", metavar='<rlnDataColumn>')
#@click.option('--o', '--output', 'out', is_flag=False, flag_value=None, help="Optional name to add for the output files.", metavar='<output_starfile.star>')


def cli(input_file, operation, data_column):

    file_list = []
    for file in input_file:
        click.echo(f"  Reading \"{file}\".")
        validate_extension(file, '.star')
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

        if isinstance(file_list[0], pd.DataFrame):
            dfA, A_type = file_list[0], 'list'
            click.echo(f'\n    {len(dfA):,} items in file A.')
        elif isinstance(file_list[0], dict):
            if 'micrographs' in file_list[0].keys():
                dfA, A_type = file_list[0]['micrographs'], 'micrographs'
                click.echo(f'\n    {len(dfA):,} micrographs in file A.')
            elif 'particles' in file_list[0].keys():
                dfA, A_type = file_list[0]['particles'], 'particles'
                click.echo(f'\n    {len(dfA):,} particles in file A.')

        if isinstance(file_list[1], pd.DataFrame):
            dfB, B_type = file_list[1], 'list'
            click.echo(f'    {len(dfB):,} items in file B.')
        elif isinstance(file_list[1], dict):
            if 'micrographs' in file_list[1].keys():
                dfB, B_type = file_list[1]['micrographs'], 'micrographs'
                click.echo(f'    {len(dfB):,} micrographs in file B.')
            elif 'particles' in file_list[1].keys():
                dfB, B_type = file_list[1]['particles'], 'particles'
                click.echo(f'    {len(dfB):,} particles in file B.')


        data_columns = list(set(data_column))

        # Take A intersection with B
        AnB = dfA.merge(dfB[data_columns], on=data_columns, how="inner")
        A_unique = (dfA.merge(dfB[data_columns], on=data_columns, how="left", indicator=True)
                   .query('_merge == "left_only"')
                   .drop(columns="_merge"))

        if A_type == 'list':
            click.echo(f'\n  File A is not the usual RELION STAR format. Skipping writing...')
        else:
            AnB_starfile = {
            'optics' : file_list[0]['optics'],
            A_type: AnB}
            starfile.write(AnB_starfile, "AnB_keepingA.star")

            A_unique_starfile = {
            'optics' : file_list[0]['optics'],
            A_type: A_unique}
            starfile.write(A_unique_starfile, "A_unique.star")

            click.echo(f'\n  Wrote A intersect B (keeping A) to \"AnB_keepingA.star\".')
            click.echo(f'    {len(AnB):,} particles in A intersect B.')
            click.echo(f'  Wrote A unique to \"A_unique.star\".')
            click.echo(f'    {len(A_unique):,} particles in A unique.')


        # Take B intersection with A
        BnA = dfB.merge(dfA[data_columns], on=data_columns, how="inner")
        B_unique = (dfB.merge(dfA[data_columns], on=data_columns, how="left", indicator=True)
           .query('_merge == "left_only"')
           .drop(columns="_merge"))

        if B_type == 'list':
            click.echo(f'\n  File B is not the usual RELION STAR format. Skipping writing...')
        else:
            BnA_starfile = {
            'optics' : file_list[1]['optics'],
            B_type: BnA}
            starfile.write(BnA_starfile, "AnB_keepingB.star")

            B_unique_starfile = {
            'optics' : file_list[1]['optics'],
            B_type: B_unique}
            starfile.write(B_unique_starfile, "B_unique.star")

            click.echo(f'\n  Wrote B intersect A (keeping B) to \"BnA_keepingB.star\".')
            click.echo(f'    {len(BnA):,} particles in A intersect B.')
            click.echo(f'  Wrote B unique to \"B_unique.star\".')
            click.echo(f'    {len(B_unique):,} particles in B unique.')


if __name__ == '__main__':
    cli(max_content_width=120)
