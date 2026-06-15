import numpy as np
import click
from starfile_rs import read_star
import starfile
import pandas as pd

def get_data_columns():
    pass
#         click.echo("\n  The following are valid data_column names:")
#         for item in valid_data_columns:
#             print(f"   {item}")
#         exit()


def validate_extension(path, extension):
    if path.endswith(extension):
        return path
    else:
        click.echo(f"  {click.style('ERROR:', fg='red', bold=True)} Wrong file format. \"{path}\" does not end with \"{extension}\".")
        raise ValueError()


@click.command(no_args_is_help=True)
# @click.option('--i', '--input', 'input_file', multiple=True, required=True, type=click.Path(exists=True, resolve_path=False), help="Path to input .star files. Multiple inputs can be passed for set operations.", metavar='<starfile.star>')
@click.option('--a', '--input_a', 'input_file_a', required=True, type=click.Path(exists=True, resolve_path=False), help="Path to input .star file A.", metavar='<starfile_A.star>')
@click.option('--b', '--input_b', 'input_file_b', required=True, type=click.Path(exists=True, resolve_path=False), help="Path to input .star file B.", metavar='<starfile_B.star>')
@click.option('--n', '--intersect', 'operation', flag_value='intersect', default=True, help="Intesect file A with file B. Four files will be written. AnB(keeping A).star, A_unique.star, BnA(keeping B).star, and B_unique.star.")
@click.option('--u', '--unique', 'operation', flag_value='unique', help="operation xyz")
@click.option('--data_column', 'data_column', multiple=True, required=True, type=str, help="RELION data column to select. \"list\" will print valid data column names.", metavar='<rlnDataColumn>')
#@click.option('--o', '--output', 'out', is_flag=False, flag_value=None, help="Optional name to add for the output files.", metavar='<output_starfile.star>')


def cli(input_file_a, input_file_b, operation, data_column):
    
    # Read file A
    click.echo(f"  Reading \"{input_file_a}\" as file A.")
    validate_extension(input_file_a, '.star')
    star_a = starfile.read(input_file_a)
    
    # Read file B
    click.echo(f"  Reading \"{input_file_b}\" as file B.")
    validate_extension(input_file_b, '.star')
    star_b = starfile.read(input_file_b)

    # Read files
    if isinstance(star_a, pd.DataFrame):
        dfA, A_type = star_a, 'list'
        click.echo(f'    {len(dfA):,} items in file A.')
    elif isinstance(star_a, dict):
        if 'micrographs' in star_a.keys():
            dfA, A_type = star_a['micrographs'], 'micrographs'
            click.echo(f'    {len(dfA):,} micrographs in file A.')
        elif 'particles' in star_a.keys():
            dfA, A_type = star_a['particles'], 'particles'
            click.echo(f'    {len(dfA):,} particles in file A.')

    if isinstance(star_b, pd.DataFrame):
        dfB, B_type = star_b, 'list'
        click.echo(f'    {len(dfB):,} items in file B.')
    elif isinstance(star_b, dict):
        if 'micrographs' in star_b.keys():
            dfB, B_type = star_b['micrographs'], 'micrographs'
            click.echo(f'    {len(dfB):,} micrographs in file B.')
        elif 'particles' in star_b.keys():
            dfB, B_type = star_b['particles'], 'particles'
            click.echo(f'    {len(dfB):,} particles in file B.')
    
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

    # if operation == 'unique':
    #     if (length := len(input_file)) > 1:
    #         click.echo(f"\n  Merging starfiles.")
    #         merged = {}
    #         for data in file_list:
    #                 for key, df in data.items():
    #                     if key in merged:
    #                         merged[key] = pd.concat([merged[key], df], ignore_index=True)
    #                     else:
    #                         merged[key] = df.copy()
    #     else:
    #         merged = star_a

    #     total_particles = len(merged['particles'])
    #     click.echo(f'    {total_particles:,} total particles.')

    #     # Drop duplicates
    #     for key in merged:
    #         if key == 'optics':
    #             merged[key] = merged[key].drop_duplicates(subset='rlnOpticsGroupName')
    #         if key == 'particles':
    #             merged[key] = merged[key].drop_duplicates(subset='rlnImageName')

    #     unique_particles = len(merged['particles'])
    #     click.echo(f'    {total_particles-unique_particles:,} duplicate particles.')
    #     click.echo(f'    {unique_particles:,} unique particles.')

    #     click.echo(f'\n  Wrote {unique_particles:,} particles to \"unique.star\".')
    #     starfile.write(merged, "unique.star")

    if operation == 'intersect':
        click.echo(f'\n  Intersecting files on {", ".join(f'"{x}"' for x in data_columns)}...')

        # Take A intersection with B
        AnB = dfA.merge(dfB[data_columns], on=data_columns, how="inner")
        A_unique = (dfA.merge(dfB[data_columns], on=data_columns, how="left", indicator=True)
                   .query('_merge == "left_only"')
                   .drop(columns="_merge"))

        if A_type == 'list':
            click.echo(f'\n  File A is not the usual RELION STAR format. Skipping writing...')
        else:
            AnB_starfile = {
            'optics' : star_a['optics'],
            A_type: AnB}
            starfile.write(AnB_starfile, "AnB_keepingA.star")

            A_unique_starfile = {
            'optics' : star_a['optics'],
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
            'optics' : star_b['optics'],
            B_type: BnA}
            starfile.write(BnA_starfile, "AnB_keepingB.star")

            B_unique_starfile = {
            'optics' : star_b['optics'],
            B_type: B_unique}
            starfile.write(B_unique_starfile, "B_unique.star")

            click.echo(f'\n  Wrote B intersect A (keeping B) to \"BnA_keepingB.star\".')
            click.echo(f'    {len(BnA):,} particles in A intersect B.')
            click.echo(f'  Wrote B unique to \"B_unique.star\".')
            click.echo(f'    {len(B_unique):,} particles in B unique.')


if __name__ == '__main__':
    cli(max_content_width=120)
