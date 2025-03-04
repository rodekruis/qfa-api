def clean_kobo_data(kobo_data):
    """Clean Kobo data by removing group names and converting keys to lowercase."""
    kobo_data_clean = {k.lower(): v for k, v in kobo_data.items()}
    # remove group names
    for key in list(kobo_data_clean.keys()):
        new_key = key.split("/")[-1]
        kobo_data_clean[new_key] = kobo_data_clean.pop(key)
    return kobo_data_clean
