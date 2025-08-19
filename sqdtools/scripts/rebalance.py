import healpy as hp
import numpy as np
import matplotlib.pyplot as plt
import math
import starfile
from itertools import cycle
import pandas as pd
from mpl_toolkits.axes_grid1 import make_axes_locatable
import click


# def calculate_percentile(bin_edges, bin_counts, percentile):
#     """
#     Thanks chatGPT.
#     """
#     # Ensure inputs are numpy arrays
#     bin_edges = np.asarray(bin_edges)
#     bin_counts = np.asarray(bin_counts)

#     # Calculate the cumulative sum of the bin counts
#     cumulative_counts = np.cumsum(bin_counts)

#     # Normalize cumulative counts to get cumulative distribution function (CDF)
#     cdf = cumulative_counts / cumulative_counts[-1]

#     # Find the bin where the desired percentile lies
#     bin_index = np.searchsorted(cdf, percentile / 100.0)

#     # Calculate the percentile within the identified bin
#     if bin_index == 0:
#         percentile_value = bin_edges[0]
#     else:
#         lower_edge = bin_edges[bin_index - 1]
#         upper_edge = bin_edges[bin_index]
#         lower_cdf = cdf[bin_index - 1]
#         upper_cdf = cdf[bin_index]

#         # Linear interpolation to find the exact percentile value within the bin
#         percentile_value = lower_edge + (percentile / 100.0 - lower_cdf) * (upper_edge - lower_edge) / (upper_cdf - lower_cdf)

#     return percentile_value


# def histogram2d(df, data_column_x, data_column_y, gridsize=50):
#     fig, ax = plt.subplots(1, 1, sharex=True, tight_layout=True)
#     hb = ax.hexbin(df[data_column_x], df[data_column_y], bins='log', gridsize=gridsize)  # cmap=colormap, gridsize=gridsize)
#     # ax.set_title(f"Class {', '.join(str(x) for x in classes)}: {data_column_x} vs. {data_column_y}")
#     ax.set_xlabel(data_column_x)
#     ax.set_ylabel(data_column_y)
#     plt.ylim(0, 180)
#     plt.xlim(-180, 180)
#     # fig.gca().set_aspect('equal', adjustable='box')
#     divider = make_axes_locatable(ax)
#     cax = divider.append_axes('right', size='5%', pad=0.1)
#     cb = fig.colorbar(hb, ax=ax, cax=cax)
#     cb.set_label('Particles')

#     return fig


def histogram2d(fig, axis, df, data_x, data_y, title, xlabel, ylabel, plot_position=(0, 0), gridsize=50):
    grid_y, grid_x = plot_position
    ax = fig.add_subplot(3, grid_y, grid_x)
    hb = ax.hexbin(df[data_x], df[data_y], bins='log', gridsize=gridsize)  # cmap=colormap, gridsize=gridsize)
    ax.set_title(title)
    # axis.set_title(f"Class {', '.join(str(x) for x in classes)}: {data_column_x} vs. {data_column_y}")
    ax.set_xlabel(xlabel)
    ax.set_xticks(range(-180, 181, 90))
    ax.set_ylabel(ylabel)
    ax.set_yticks(range(0, 181, 90))
    plt.ylim(0, 180)
    plt.xlim(-180, 180)
    ax.set_aspect('equal', adjustable='box')

    divider = make_axes_locatable(ax)
    cax = divider.append_axes('right', size='4%', pad=0.1)
    cb = plt.colorbar(hb, ax=ax, cax=cax)
    # cb.set_label('Particles')


# def read(input, data_column_x, data_column_y):
#     star_df = starfile.read(input)
#     data = star_df['particles'][[data_column_x, data_column_y]]
#     return data


def dict_from_counts(df, npix, subset='healpix') -> dict:
    """
    Turns the dataframe into a dictionary of counts. dict('healpix': 'count')
    Restores the missing values with zero.
    """
    counts_dict = df.value_counts(subset=subset, sort=False).to_dict()

    # add missing pixels to dictionary
    missing_pix = {pix: 0 for pix in range(npix) if pix not in counts_dict.keys()}
    counts_dict.update(missing_pix)

    return counts_dict


def threshold_counts(counts_dict, percentile):
    """
    Returns the counts in the bin, that if thresholded by this count
    will return x percent of the data.
    """

    sorted_counts = list(sorted(counts_dict.values()))
    total_particles = partial_sum = sum(sorted_counts)

    for i, pix_count in enumerate(reversed(sorted_counts), start=1):
        # sum up to the last bin
        partial_sum -= pix_count
        percent = (partial_sum + (sorted_counts[-(i + 1)] * i)) / total_particles

        if percent < percentile:
            threshold_count = sorted_counts[-(i)]
            break

    return threshold_count


@click.command(no_args_is_help=True)
@click.option('--i', '--input', 'input', required=True, type=click.Path(exists=True, resolve_path=False), help="Path to the input .star file", metavar='<starfile.star>')
@click.option('--t', '--threshold', 'threshold', required=True, default=0.8, type=float, help="Percent particles to keep.", metavar='0.8')
@click.option('--ns', '--no_save', 'suppress_out', flag_value=True, help="Analyze only. Do not save the plots or STAR files.")
@click.option('--p', '--prefix', 'prefix', help="Prefix for the output files.", metavar='<prefix_output.star>')
def cli(input, prefix, suppress_out, threshold):

    # read in the starfile
    click.echo(f"  Reading \"{input.split('/')[-1]}\".")  # Gets file name from the path
    df = starfile.read(input)

    # take the particle table
    particles_df = df['particles']
    data_column_x = 'rlnAngleRot'
    data_column_y = 'rlnAngleTilt'

    click.echo("\n  Binning by orientation...")
    # add posese columns that are compatable with healpix
    particles_df[f"{data_column_x}_RAD"] = particles_df[data_column_x].apply(lambda x: math.radians(x + 180))
    particles_df[f"{data_column_y}_RAD"] = particles_df[data_column_y].apply(lambda y: math.radians(y))

    # healpix settings
    k = 3
    nside = 2**k
    npix = hp.nside2npix(nside)
    theta = particles_df[f"{data_column_y}_RAD"]
    phi = particles_df[f"{data_column_x}_RAD"]
    #print(f"There are {npix} pixels")
    # get a list of healpix indexes: 0 -> npix-1, npix total
    pixels = hp.ang2pix(nside, theta, phi)

    # add this back to the particles_df
    particles_df['healpix'] = pixels

    # dictionary of particle counts per healpix -> dict('healpix': 'count')
    healpix_counts_dict = dict_from_counts(particles_df, npix)

    # map counts of each healpix to each particle
    particles_df['healpix_counts'] = particles_df['healpix'].map(healpix_counts_dict)

    """
    I don't real;y understand how cryosparc is calculating the 'rebalance percentile'
    I am taking the views such that X% of the data is returned, ie horozontal integration from the right.
    """
    click.echo(f"  Thresholding orientations to {threshold * 100}%")  # Gets file name from the path
    percent = threshold
    threshold_count = threshold_counts(healpix_counts_dict, percent)

    # set aside the views le percentile
    included_df = particles_df[particles_df['healpix_counts'] <= threshold_count]
    for_resampling = particles_df[particles_df['healpix_counts'] > threshold_count]
    resampled = for_resampling.groupby('healpix').sample(n=threshold_count)

    included_df = pd.concat([included_df, resampled])
    excluded_df = particles_df[~particles_df.index.isin(included_df.index)]
    dict_from_counts(particles_df, npix)
    included_dict = dict_from_counts(included_df, npix)
    excluded_dict = dict_from_counts(excluded_df, npix)
    neg_excluded_dict = {key: value * -1 for key, value in excluded_dict.items()}
    for_plt_ex = sorted(neg_excluded_dict.values(), reverse=True)
    data_array = np.array(for_plt_ex, dtype=float)
    data_array[data_array == 0] = np.nan
    for_plt_ex = data_array.tolist()

    marker = cycle(('.', 'x'))

    click.echo("\n  Making plots.")
    fig = plt.figure(figsize=(8, 6), layout='tight')
    axis = 1
    axis_labels = ('$\\phi$ (rlnAngleRot, deg)', '$\\theta$ (rlnAngleTilt, deg)')
    histogram2d(fig, axis, particles_df, data_column_x, data_column_y, 'All Particles', *axis_labels, (2, 1))
    histogram2d(fig, axis, included_df, data_column_x, data_column_y, 'Included Particles', *axis_labels, (2, 3))
    histogram2d(fig, axis, excluded_df, data_column_x, data_column_y, 'Excluded Particles', *axis_labels, (2, 4))

    ax = fig.add_subplot(3, 2, 2)
    #sorted_hp_counts_dict = sorted(healpix_counts_dict)
    ax.plot(sorted(included_dict.values()), marker=next(marker))
    ax.plot(for_plt_ex, marker=next(marker))
    plt.fill_between(range(npix), sorted(included_dict.values()), color='skyblue', alpha=0.2)
    plt.fill_between(range(npix), sorted(neg_excluded_dict.values(), reverse=True), color='orange', alpha=0.2)
    ax.set(xlabel='view (HEALPix index)', ylabel='# of particles', title='counts')

    # sorting output file names
    if not prefix:
        prefix = ""
    else:
        prefix = f"{prefix}_"

    pdf_filename = f"{prefix}rebalance.pdf"
    included_filename = f"{prefix}included.star"
    excluded_filename = f"{prefix}excluded.star"

    if not suppress_out:
        # histogram.figsize = (11.80, 8.85)
        # histogram.dpi = 300
        plt.show()
        click.echo(f"\n  Saving plots to {pdf_filename}.")
        plt.savefig(pdf_filename)
    else:
        click.echo("\n  Saving outputs is suppressed.")
        plt.show()

    if not suppress_out:
        included_df = included_df.drop(columns=['rlnAngleRot_RAD', 'rlnAngleTilt_RAD', 'healpix', 'healpix_counts'])
        excluded_df = excluded_df.drop(columns=['rlnAngleRot_RAD', 'rlnAngleTilt_RAD', 'healpix', 'healpix_counts'])

        click.echo(f"  Writing {len(included_df)} rebalanced particles to \"{included_filename}\"...")
        df['particles'] = included_df
        starfile.write(df, included_filename)

        click.echo(f"  Writing {len(excluded_df)} excluded particles to \"{excluded_filename}\"...")
        df['particles'] = excluded_df
        starfile.write(df, excluded_filename)


if __name__ == '__main__':
    cli(max_content_width=180)
