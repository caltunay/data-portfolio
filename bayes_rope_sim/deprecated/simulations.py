import pymc as pm
import pandas as pd
import numpy as np

import arviz as az
import matplotlib.pyplot as plt
import seaborn as sns

def calculate_expected_loss(control_simulation, treatment_simulation, treatment_won, min_difference_delta=0):
    # calculate loss for control and treatment based on the simulation values
    loss_control = [max((j - min_difference_delta) - i, 0) for i,j in zip(control_simulation, treatment_simulation)]
    loss_treatment = [max(i - (j - min_difference_delta), 0) for i,j in zip(control_simulation, treatment_simulation)]

    all_loss_control = [int(i)*j for i,j in zip(treatment_won, loss_control)]
    all_loss_treatment = [(1 - int(i))*j for i,j in zip(treatment_won, loss_treatment)]

    expected_loss_control = np.mean(all_loss_control)
    expected_loss_treatment = np.mean(all_loss_treatment)
    return expected_loss_control, expected_loss_treatment


def calculate_ab_test_expected_loss(samples_A, samples_B, epsilon=0.05, min_difference_delta=0):
    # Calculate treatment_won based on whether B has higher conversion rates than A
    treatment_won = [int(i < j) for i,j in zip(samples_A, samples_B)]
    
    # Calculate expected loss for both control (A) and treatment (B)
    expected_loss_A, expected_loss_B = calculate_expected_loss(samples_A, samples_B, treatment_won, min_difference_delta)
    
    return expected_loss_A, expected_loss_B


def simulate_experiment(g, date_col='date', group_col='group', rope_bounds=(-0.02, 0.02)):

    # init priors
    alpha_prior_control, beta_prior_control = 1, 1
    alpha_prior_treatment, beta_prior_treatment = 1, 1
    
    # log dataframe
    log_columns = [
        "date", "mean_sample_size",
        "posterior_mean_control", "posterior_mean_treatment", "posterior_mean_difference",
        "hdi_94_lower_control", "hdi_94_upper_control",
        "hdi_94_lower_treatment", "hdi_94_upper_treatment",
        "hdi_94_lower_difference", "hdi_94_upper_difference",
        "probability_treatment_better", "in_rope_percentage",
        "expected_loss_A", "expected_loss_B"
    ]
    log_df = pd.DataFrame(columns=log_columns)
    
    # date order
    dates = sorted(g[date_col].unique())

    cumulative_control_conversions, cumulative_control_observations = 0, 0
    cumulative_treatment_conversions, cumulative_treatment_observations = 0, 0
    
    # rope boundaries
    rope_bounds = rope_bounds  # Adjust based on conversion rate scale
    
    # main loop
    for date in dates:
        print(f"Processing date: {date}")
    
        # slice for date
        control_data = g[(g[date_col] == date) & (g[group_col] == 'control')]
        treatment_data = g[(g[date_col] == date) & (g[group_col] == 'treatment')]
    
        if control_data.empty or treatment_data.empty:
            print(f"Skipping {date} due to missing data.")
            continue
    
        control_conversions = control_data['conversion'].values[0]
        control_observations = control_data['observation'].values[0]
        treatment_conversions = treatment_data['conversion'].values[0]
        treatment_observations = treatment_data['observation'].values[0]

        cumulative_control_conversions += control_conversions
        cumulative_control_observations += control_observations
        cumulative_treatment_conversions += treatment_conversions
        cumulative_treatment_observations += treatment_observations
    
        mean_sample_size = np.mean([control_observations, treatment_observations])
    
        # pymc model
        with pm.Model() as model:
            p_control = pm.Beta('p_control', alpha=alpha_prior_control, beta=beta_prior_control)
            p_treatment = pm.Beta('p_treatment', alpha=alpha_prior_treatment, beta=beta_prior_treatment)
            
            obs_control = pm.Binomial('obs_control', n=cumulative_control_observations, p=p_control, observed=cumulative_control_conversions)
            obs_treatment = pm.Binomial('obs_treatment', n=cumulative_treatment_observations, p=p_treatment, observed=cumulative_treatment_conversions)
            
            difference = pm.Deterministic('difference', p_treatment - p_control)
            
            trace = pm.sample(2000, tune=1000, return_inferencedata=True, progressbar=False)
    
        # extract posteriors
        summary = az.summary(trace, var_names=["p_control", "p_treatment", "difference"], hdi_prob=0.94)
    
        posterior_mean_control = summary.loc["p_control", "mean"]
        posterior_mean_treatment = summary.loc["p_treatment", "mean"]
        posterior_mean_difference = summary.loc["difference", "mean"]
    
        hdi_94_lower_control, hdi_94_upper_control = summary.loc["p_control", ["hdi_3%", "hdi_97%"]]
        hdi_94_lower_treatment, hdi_94_upper_treatment = summary.loc["p_treatment", ["hdi_3%", "hdi_97%"]]
        hdi_94_lower_difference, hdi_94_upper_difference = summary.loc["difference", ["hdi_3%", "hdi_97%"]]
    
        # P(B > A)
        probability_treatment_better = (trace.posterior["difference"] > 0).mean().values
    
        # in ROPE %
        in_rope_percentage = ((trace.posterior["difference"] > rope_bounds[0]) & (trace.posterior["difference"] < rope_bounds[1])).mean().values
    
        # extract posterior samples
        samples_control = trace.posterior['p_control'].values.flatten()
        samples_treatment = trace.posterior['p_treatment'].values.flatten()
        
        # expected loss cal
        expected_loss_A, expected_loss_B = calculate_ab_test_expected_loss(samples_control, samples_treatment)
    
        # append to log
        log_entry = pd.DataFrame([[
            date, mean_sample_size,
            posterior_mean_control, posterior_mean_treatment, posterior_mean_difference,
            hdi_94_lower_control, hdi_94_upper_control,
            hdi_94_lower_treatment, hdi_94_upper_treatment,
            hdi_94_lower_difference, hdi_94_upper_difference,
            probability_treatment_better, in_rope_percentage,
            expected_loss_A, expected_loss_B
        ]], columns=log_columns)
    
        log_df = pd.concat([log_df, log_entry], ignore_index=True)
    
        # update priors
        alpha_prior_control += control_conversions
        beta_prior_control += (control_observations - control_conversions)
        alpha_prior_treatment += treatment_conversions
        beta_prior_treatment += (treatment_observations - treatment_conversions)
    
        # plot posterior difference
        az.plot_posterior(
            trace.posterior,
            var_names=["difference"],
            hdi_prob=0.94,
            rope=rope_bounds,
            ref_val=0
        )
        plt.title(f'Posterior Difference on {date}')
        plt.show()
    
        if in_rope_percentage >= .95 or in_rope_percentage <= .05:
            break

    log_df['total_sample_size'] = log_df['mean_sample_size'].cumsum()
    return log_df