import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

def plot_rope(d_list, rope_thresholds=(.05, .95)):

    sample_sizes = {} 
    for _ in d_list:
        if float(_['in_rope_percentage'].values[-1]) >= .95 or float(_['in_rope_percentage'].values[-1]) <= .05:
            if 'reached_stat_sig' not in sample_sizes:
                sample_sizes['reached_stat_sig'] = [_['total_sample_size'].values[-1]]
            else:
                sample_sizes['reached_stat_sig'].append(_['total_sample_size'].values[-1])
        else:
            if 'didnot_reached_stat_sig' not in sample_sizes:
                sample_sizes['didnot_reached_stat_sig'] = [_['total_sample_size'].values[-1]]
            else:
                sample_sizes['didnot_reached_stat_sig'].append(_['total_sample_size'].values[-1])

    avg_sample_size = np.mean(sample_sizes['reached_stat_sig'])
    
    # start fig and ax
    fig, ax1 = plt.subplots(figsize=(12, 6))

    # loop through and plot
    color_map = plt.cm.get_cmap("tab10", len(d_list))  # Generate different colors for each line
    for idx, d in enumerate(d_list):
        color = color_map(idx)
        ax1.plot(d['total_sample_size'], d['in_rope_percentage'], marker='s', linestyle='--', color=color)

    # rope thresholds
    ax1.axhline(y=rope_thresholds[1], color='darkred', linestyle=':', linewidth=1.5, label="ROPE Threshold (95%)")
    ax1.axhline(y=rope_thresholds[0], color='darkred', linestyle=':', linewidth=1.5, label="ROPE Threshold (5%)")
    
    # titles
    fig.suptitle("Posterior ROPE Percentage Over Sample Sizes")
    fig.tight_layout()
    fig.legend(loc="lower left", bbox_to_anchor=(0.1, 0.95))
    plt.xticks(rotation=45)
    plt.show()
    st.pyplot(fig)
    
    print(f"Average sample size to conclusive experiment: {avg_sample_size}")
