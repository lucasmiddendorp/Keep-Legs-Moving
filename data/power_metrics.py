def calc_np(power_series):
    # Rolling 30-second average and fourth power mean
    return (np.mean(np.power(pd.Series(power_series).rolling(30).mean().dropna(), 4))) ** 0.25

def calc_if(np, ftp):
    return np / ftp

def calc_tss(duration_s, np, ftp):
    return (duration_s * np * calc_if(np, ftp)) / (ftp * 3600) * 100
