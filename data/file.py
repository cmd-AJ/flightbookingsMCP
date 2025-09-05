import pandas as pd
import re

# Read CSV
df = pd.read_csv("flights.csv")

# Extract Duration, From, To from Flight_Duration
def split_duration(fd):
    match = re.match(r"(\d+h \d+m)([A-Z]{3})-([A-Z]{3})", fd)
    if match:
        return match.group(1), match.group(2), match.group(3)
    return fd, None, None

df[["Flight_Duration", "From", "To"]] = df["Flight_Duration"].apply(lambda x: pd.Series(split_duration(x)))

# Extract Time_from, Time_to, Day_offset from Time_total
def split_time(tt):
    match = re.match(r"(.+?)\s*–\s*(\d{1,2}:\d{2}\s*[ap]m)(\+1)?", tt)
    if match:
        return match.group(1).strip(), match.group(2).strip(), match.group(3) if match.group(3) else ""
    return None, None, None

df[["Time_from", "Time_to", "Day_offset"]] = df["Time_total"].apply(lambda x: pd.Series(split_time(x)))

print(df.head())


df.to_csv("flights_clean.csv", index=False)