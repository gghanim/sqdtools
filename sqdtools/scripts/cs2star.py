# made with love, and pain, by george. thank you cryosparc.
import numpy as np
import click
import os
import starfile
import json


def get_relion_paths(json_file) -> dict[str]:
    """
    Gets RELION directory and STAR file paths from cryoSPARC 'job.json' file.
    Corrosponding variable names are specified automatically.
    """

    try:
        click.echo("  Attempting to get RELION directory and STAR file...")

        # read in job.json file
        with open(json_file, 'r') as file:
            data = json.load(file)

            # parse two specific paths I need here
            param_sepc = data.get('params_spec', None)

            # 'particle_blob_path' is the RELION directory
            particle_blob_path = param_sepc.get('particle_blob_path', None).get('value', None)

            # 'particle_meta_path' is the STAR file
            particle_meta_path = param_sepc.get('particle_meta_path', None).get('value', None)

        # exit if not found or if STAR file is not .star
        if particle_blob_path is None or particle_meta_path is None or not particle_meta_path.endswith('.star'):
            click.echo(f"  {click.style('WARNING:', fg='red', bold=True)} Could not automatically get RELION directory or STAR file.")
            click.echo("  Rerun the script with the '--r' and '--s' flags ")
            exit()

        # report paths being used
        else:
            click.echo(f"    Success. Using RELION directory: \"{particle_blob_path}\"")
            click.echo(f"    Success. Using STAR file: \"{particle_meta_path}\"")

            # return a dictionary with values
            return {"relion_project_dir": particle_blob_path, "star": particle_meta_path}

    except Exception as e:
        click.echo(f"  An error occurred: {e}")
        exit()


def set_paths(paths_from_json, paths_from_cli):
    """
    Sets the paths of --s and --r if they are None.
    """
    for key in paths_from_cli:
        if not paths_from_cli.get(key):
            # if None, sets option path to the one from json file
            paths_from_cli.update({key: paths_from_json.get(key)})
    return paths_from_cli.get('star'), paths_from_cli.get('relion_project_dir')


def resolve_symlinks(file_path, cs_project_path, relion_project_dir):
    path = file_path.split()[0].split('@')[1]
    abs_path = os.path.join(cs_project_path, path)  # Generate an absolute path for CS import

    if not os.path.exists(abs_path):
        click.echo(f"  {click.style('ERROR:', fg='red', bold=True)} The file \"{abs_path}\" does not exist.\nAre you in your cryoSPARC directory? \nTry using the \"--cs_project_dir\" flag")

        raise FileNotFoundError()

    if os.path.islink(abs_path):
        original_path = os.readlink(abs_path)
        modified_original_path = original_path.replace(relion_project_dir + '/', '')  # Makes path relative to relion directory
        resolved_line = file_path.replace(path, modified_original_path)  # Replaces CS path with relion path

    return resolved_line


def validate_extension(path, extension):
    if path.endswith(extension):

        return path

    else:
        click.echo(f"  {click.style('ERROR:', fg='red', bold=True)} Wrong file format. \"{path}\" does not end with \"{extension}\".")

        raise ValueError()


def force_extension(path, extension):
    if path.endswith(extension):

        return path

    else:
        click.echo(f"  {click.style('WARNING:', fg='red', bold=True)} Output file \"{path}\" does not end with \"{extension}\". Let me fix that for you...")

        return path + extension


def activate_required_flags(ctx, param, value):
    """
    Activates required flags if auto mode is not enabled.
    """
    # attributes to modify
    attributes_to_activate = ['star', 'relion_project_dir']

    if not value:
        for p in ctx.command.params:
            if isinstance(p, click.Option) and p.name in attributes_to_activate:
                p.required = True

    return value


# Set up the CLI command
@click.command(no_args_is_help=True)
# --a automatically gets --s and --r flags and overrides --s and --r requirements
@click.option('--a', 'automatic', is_eager=True, hidden=True, is_flag=False, flag_value=True, callback=activate_required_flags)
# --i is the cryosparc file that contains 'blob' paths
@click.option('--i', '--input', 'passthrough', required=True, type=click.Path(exists=True, resolve_path=True), help="Path to the cryosparc file that contains 'blobs'")
# --s is the STAR file to take an intersection of
@click.option('--s', '--star', 'star', required=False, type=click.Path(exists=True, resolve_path=True), help="Path to the RELION STAR file. Output will be a subset of this file")
# --r is path to RELION directory, used for resolving the symbolic links created by cryosparc
@click.option('--r', '--relion_project_dir', 'relion_project_dir', required=False, type=click.Path(exists=True, resolve_path=True), help="Path to the RELION project directoy")
# --c is path to cryoSPARC directory, but script should get for you
@click.option('--c', '--cs_project_dir', 'cs_project_path', required=False, type=click.Path(exists=True, resolve_path=True), help="Path to the cryoSPARC project directoy")
# --o name of the output STAR file
@click.option('--o', '--out', 'out', default='filtered_particles.star', show_default=True, help="Optional name for the output STAR file", metavar='<filtered_particles.star>')
def cli(passthrough, star, relion_project_dir, out, cs_project_path, automatic):
    """
    Converts cryoSPARC '.cs' to RELION '.star' by an intersection operation.
    Only particle STAR files are supported.
    Alignment and CTF information from cryoSPARC are not preserved.
    Converting .cs files that descend from multiple import jobs is not supported.
    """

    # Validate the inputs
    out = force_extension(out, '.star')
    passthrough = validate_extension(passthrough, '.cs')

    if star:
        star = validate_extension(star, '.star')

    # get the cs path if not set
    if not cs_project_path:
        cs_project_path = os.path.dirname(os.path.dirname(os.path.abspath(passthrough)))  # i know, i'm sorry

    # merge index and path of cs paticles into a list to intersect
    # read in the .cs numpy array
    click.echo(f"  Reading \"{passthrough.split('/')[-1]}\".")  # Gets file name from the path
    cs = np.load(passthrough)

    # parse blob paths into a list
    blobPath = [path.decode('utf-8') for path in cs['blob/path']]

    # parse og indexes for each blob into a list
    blobIdx = cs['blob/idx'] + 1

    # zip them together to look like relion
    merged = [f"{index}@{path}" for index, path in zip(blobIdx, blobPath)]

    # try to get relion paths
    if automatic:

        # get the name of unique import jobs
        unique_import_jobs = {path.split('/')[0] for path in blobPath}

        # exit if more than 1 import job found
        if len(unique_import_jobs) > 1:
            click.echo(f"  {click.style('ERROR:', fg='red', bold=True)} Multiple import jobs found: {unique_import_jobs}. Converting from multiple import jobs is not supported.")
            exit()

        # parse the STAR and RELION data from job.json file
        else:
            # set path of import job.json file
            json_path = f"{cs_project_path}/{unique_import_jobs.pop()}/job.json"

            # gets the specific parameters from cryoSPARC import job.json file
            paths_from_json = get_relion_paths(json_path)

            # reassigns --s or --r to the values from job.json if they are None
            star, relion_project_dir = set_paths(paths_from_json, {"star": star, "relion_project_dir": relion_project_dir})

    # Resolve the cs path symbolic links to relion paths
    click.echo("\n  Resolving symbolic links...")
    resolved_paths = [resolve_symlinks(line, cs_project_path, relion_project_dir) for line in merged]

    # Intersect the star file against the list of particle paths
    click.echo(f"  Extracting a subset from \"{star.split('/')[-1]}\"...")  # Gets file name from the path
    df = starfile.read(star)

    # Strip leading zeros
    df['particles']['rlnImageName'] = df['particles']['rlnImageName'].apply(lambda s: s.lstrip("0"))

    filter = df['particles']['rlnImageName'].isin(resolved_paths)
    df['particles'] = df['particles'][filter]

    number_found = len(df['particles'])
    # Checks that both starfiles are the same size, if not something went wrong
    if len(resolved_paths) != number_found:
        click.echo(f"  {click.style('ERROR:', fg='red', bold=True)} Some particles were not found: {len(resolved_paths):,} != {number_found:,}")
        raise ValueError()

    click.echo(f"    Found {number_found:,} particles in common.")

    # Writes the new star file
    click.echo(f"\n  Writing {number_found:,} particles to \"{out}\"...")
    starfile.write(df, out)
    click.echo(f"    Done.")


if __name__ == '__main__':
    cli(max_content_width=120)
