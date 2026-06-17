# a python script to add beam tilt groups
import click
import starfile
import pandas as pd
import os

def validate_extension(path, extension):
    if path.endswith(extension):
        return path
    else:
        click.echo(f"  {click.style('ERROR:', fg='red', bold=True)} Wrong file format. \"{path}\" does not end with \"{extension}\".")
        raise ValueError()

@click.command(no_args_is_help=True)
@click.option('--b', '--beamtilt_groups', 'beamtilt_groups', required=True, type=click.Path(exists=True, resolve_path=False), help="Path to the beam tilt groups .star file", metavar='<beamtilt_groups.star>')
@click.option('--c', '--ctf', 'ctf_mics', required=True, type=click.Path(exists=True, resolve_path=False), help="Path to the CTF corrected micrographs .star file", metavar='<micrographs_ctf.star>')
@click.option('--m', '--motion_corr', 'motion_corr_mics', required=True, type=click.Path(exists=True, resolve_path=False), help="Path to the motion corrected micrographs .star file", metavar='<corrected_micrographs.star>')
@click.option('--p', '--particles', 'particles', required=True, type=click.Path(exists=True, resolve_path=False), help="Path to the particles .star file", metavar='<particles.star>')

def cli(beamtilt_groups, ctf_mics, motion_corr_mics, particles):

    # Check inputs
    input_list = [beamtilt_groups, ctf_mics, motion_corr_mics, particles]
    for file in input_list:
        validate_extension(file, '.star')

    # Read files
    click.echo(f"  Read \"{beamtilt_groups}\" as beam tilt groups.")
    beamtilt_df = starfile.read(beamtilt_groups)
    ctf_df = starfile.read(ctf_mics)
    motCorr_df = starfile.read(motion_corr_mics)
    click.echo(f"  Read \"{particles}\" as particles.")
    particles_df = starfile.read(particles)

    # Merge optics groups
    click.echo(f"\n  Preparing new optics table...")
    bt_optics_df = beamtilt_df['optics']
    ptcls_optics_df = particles_df['optics']
    merged = ptcls_optics_df.merge(bt_optics_df[['rlnOpticsGroupName', 'rlnOpticsGroup']], how='right')

    # Fill in NaNs with ptcls dataframe
    cols_with_nan = merged.columns[merged.isna().any()].tolist()
    for col in cols_with_nan:
        merged[col] = merged[col].fillna(ptcls_optics_df[col].iloc[0])
    new_ptcls_optics = merged
    click.echo(f"    done.")

    # Prepare the beam tilt lookup table
    click.echo(f"\n  Adding optics groups to particles.star file...")
    bt_lookup_df = beamtilt_df['movies']
    bt_lookup_df['rlnMicrographMovieName'] = bt_lookup_df['rlnMicrographMovieName'].apply(lambda x: os.path.splitext(os.path.basename(x))[0]).str.replace(".", "_")
    lookup = bt_lookup_df.set_index('rlnMicrographMovieName')['rlnOpticsGroup']

    # Prepare the particles for lookup
    ptcls_df = particles_df['particles']
    ptcls_df['lookup'] = ptcls_df['rlnMicrographName'].apply(lambda x: os.path.splitext(os.path.basename(x))[0])

    # Populate the values by lookup and clean up
    mask = ptcls_df['lookup'].isin(lookup.index)
    ptcls_df.loc[mask, 'rlnOpticsGroup'] = ptcls_df.loc[mask, 'lookup'].map(lookup)
    ptcls_df.drop(columns=['lookup'], inplace=True)
    click.echo(f"    done.")

    # Write particles star file
    click.echo(f'\n  Writing new particles to \"particles_bt_groups.star\".')
    new_ptcls_starfile = {
    'optics': merged,
    'particles': ptcls_df}
    starfile.write(new_ptcls_starfile, f"particles_bt_groups.star")
    click.echo(f"    done.")



if __name__ == '__main__':
    cli(max_content_width=520)
