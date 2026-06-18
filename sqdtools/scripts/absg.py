# a python script to add beam shift groups
import click
import starfile
import pandas as pd
from pathlib import Path

def validate_extension(path, extension):
    if path.endswith(extension):
        return path
    else:
        click.echo(f"  {click.style('ERROR:', fg='red', bold=True)} Wrong file format. \"{path}\" does not end with \"{extension}\".")
        raise ValueError()

def add_bs_groups(bs_optics_df, lookup, star_file):
    click.echo(f"  Read \"{Path(star_file).name}\".")
    sf_df = starfile.read(star_file)

    first_datatable_key = list(sf_df.keys())[0]
    click.echo(f"    Preparing new {first_datatable_key} table for \"{Path(star_file).name}\"...")
    sf_optics_df = sf_df[first_datatable_key]
    merged_sf_optics = sf_optics_df.merge(bs_optics_df[['rlnOpticsGroupName', 'rlnOpticsGroup']], how='right')

    # Fill in NaNs with ptcls dataframe
    cols_with_nan = merged_sf_optics.columns[merged_sf_optics.isna().any()].tolist()
    for col in cols_with_nan:
        merged_sf_optics[col] = merged_sf_optics[col].fillna(sf_optics_df[col].iloc[0])
    # click.echo(f"      done.")

    # Prepare the mics for lookup
    second_datatable_key = list(sf_df.keys())[1]
    click.echo(f"    Preparing new {second_datatable_key} table for \"{Path(star_file).name}\"...")
    sf_data_df = sf_df[second_datatable_key]
    sf_data_df['lookup'] = sf_data_df['rlnMicrographName'].apply(lambda x: Path(x).stem)

    # Populate the values by lookup and clean up
    mask = sf_data_df['lookup'].isin(lookup.index)
    sf_data_df.loc[mask, 'rlnOpticsGroup'] = sf_data_df.loc[mask, 'lookup'].map(lookup)
    sf_data_df.drop(columns=['lookup'], inplace=True)
    # click.echo(f"      done.")

    # Write particles star file
    new_starfile_name = f"{Path(star_file).stem}_bs_groups.star"
    click.echo(f'    Writing datatables with beam shift groups to \"{new_starfile_name}\".')
    new_sf = {
    'optics': merged_sf_optics,
    second_datatable_key: sf_data_df}
    starfile.write(new_sf, new_starfile_name)
    click.echo(f"      done.\n")

def activate_required_flags(ctx, param, value):
    """
    Activates required flags if auto mode is not enabled.
    """
    # attributes to modify
    attributes_to_activate = ['beamshift_groups']
    attributes_to_deactivate = ['particles']

    if not value:
        for p in ctx.command.params:
            if isinstance(p, click.Option) and p.name in attributes_to_activate:
                p.required = True
            if isinstance(p, click.Option) and p.name in attributes_to_deactivate:
                p.required = False

    return value

@click.command(no_args_is_help=True)
@click.option('--b', '--beamshift_groups', 'beamshift_groups', required=False, type=click.Path(exists=True, resolve_path=False), help="Path to the beam shift groups .star file", metavar='<beamshift_groups.star>')
@click.option('--c', '--ctf', 'ctf_mics', required=False, type=click.Path(exists=True, resolve_path=False), help="Path to the CTF corrected micrographs .star file", metavar='<micrographs_ctf.star>')
@click.option('--m', '--motion_corr', 'motion_corr_mics', required=False, type=click.Path(exists=True, resolve_path=False), help="Path to the motion corrected micrographs .star file", metavar='<corrected_micrographs.star>')
@click.option('--p', '--particles', 'particles', required=True, type=click.Path(exists=True, resolve_path=False), help="Path to the particles .star file", metavar='<particles.star>')
@click.option('--e', '--epu', 'epu', required=False, is_flag=True, is_eager=True, callback=activate_required_flags)

def cli(beamshift_groups, ctf_mics, motion_corr_mics, particles, epu):
    # Check inputs, except beamshift groups
    input_list = [ctf_mics, motion_corr_mics, particles]
    cleaned_input_list = [file for file in input_list if file is not None]

    if len(cleaned_input_list) == 0:
        click.echo(f"  {click.style('ERROR:', fg='red', bold=True)} At least one input file is required.")
        exit()

    for file in cleaned_input_list:
        validate_extension(file, '.star')

    # Prepare beam shift mappings
    if epu:
        click.echo(f"  EPU mode activated.\n  Reading beam shift groups from EPU micrograph names...")
        epu_df = starfile.read(particles)
        second_datatable_key = list(epu_df.keys())[1]
        epu_lookup_df = epu_df[second_datatable_key]
        epu_lookup_df['rlnMicrographName'] = epu_lookup_df['rlnMicrographName'].apply(lambda x: Path(x).stem)
        epu_lookup_df.drop_duplicates(subset=['rlnMicrographName'], inplace=True) # Drop duplicates to make it faster
        epu_lookup_df['rlnOpticsGroup'] = epu_lookup_df['rlnMicrographName'].apply(lambda x: Path(x).stem.split('_')[4]).astype(int)
        lookup = epu_lookup_df.set_index('rlnMicrographName')['rlnOpticsGroup']
        lookup = lookup[~lookup.index.duplicated(keep='first')]

        #Make Optics table
        optics_groups_values = [int(value) for value in epu_lookup_df['rlnOpticsGroup'].unique()]
        optics_groups_values.sort()
        bs_optics_df = pd.DataFrame({
                                    'rlnOpticsGroupName': [f'opticsGroup{value}' for value in optics_groups_values],
                                    'rlnOpticsGroup': optics_groups_values
                                    })
    else:
        validate_extension(beamshift_groups, '.star')
        # Prepare the beam shift lookup table
        beamshift_df = starfile.read(beamshift_groups)
        bs_lookup_df = beamshift_df['movies']
        bs_lookup_df['rlnMicrographMovieName'] = bs_lookup_df['rlnMicrographMovieName'].apply(lambda x: Path(x).stem).str.replace(".", "_")
        lookup = bs_lookup_df.set_index('rlnMicrographMovieName')['rlnOpticsGroup']

        # Prepare the beam shift optics table
        bs_optics_df = beamshift_df['optics']

    # Add the beam shift groups
    for file in cleaned_input_list:
        add_bs_groups(bs_optics_df, lookup, file)

if __name__ == '__main__':
    cli(max_content_width=120)
