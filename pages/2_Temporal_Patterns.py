import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st

sns.set_style("whitegrid")

st.title("Section 2. Temporal Patterns")
st.write(
    "This page explores when Citi Bike trips are most common across hours, weekdays, and months "
    "using trip data from January to March 2025."
)

# -----------------------------
# Load data
# -----------------------------
@st.cache_data
def load_data():
    hourly = pd.read_csv("data/hourly_summary.csv")
    monthly = pd.read_csv("data/monthly_summary.csv")
    return hourly, monthly

try:
    hourly, monthly = load_data()
except FileNotFoundError as e:
    st.error(f"Data file not found: {e}")
    st.stop()

# -----------------------------
# Data prep
# -----------------------------
day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
hourly["day_of_week"] = pd.Categorical(
    hourly["day_of_week"],
    categories=day_order,
    ordered=True
)
hourly["is_weekend"] = hourly["day_of_week"].isin(["Saturday", "Sunday"])

month_order = (
    monthly[["month", "month_name"]]
    .drop_duplicates()
    .sort_values("month")["month_name"]
    .tolist()
)

def to_season(m):
    if m in (12, 1, 2):
        return "Winter"
    if m in (3, 4, 5):
        return "Spring"
    if m in (6, 7, 8):
        return "Summer"
    return "Autumn"

monthly["season"] = monthly["month"].apply(to_season)

# -----------------------------
# Sidebar filters
# -----------------------------
st.sidebar.header("Temporal Filters")

show_member_split = st.sidebar.checkbox("Show member/casual split in monthly chart", value=True)

# -----------------------------
# Chart 3. Trips by Hour of Day
# -----------------------------
st.subheader("Trips by Hour of Day (Weekday vs Weekend)")

hour_wk = hourly.groupby(["hour", "is_weekend"], as_index=False)["total_rides"].sum()
hour_wk["day_type"] = hour_wk["is_weekend"].map({True: "Weekend", False: "Weekday"})

fig, ax = plt.subplots(figsize=(10, 4))
sns.lineplot(data=hour_wk, x="hour", y="total_rides", hue="day_type", marker="o", ax=ax)
ax.set_xlabel("Hour of day")
ax.set_ylabel("Number of trips")
ax.set_xticks(range(0, 24))
st.pyplot(fig, use_container_width=True)
plt.close(fig)

st.write(
    "This chart compares weekday and weekend usage across the day. It helps show whether bike-share "
    "activity follows a commuting pattern or a more leisure-oriented pattern."
)

# -----------------------------
# Chart 4. Trips by Day of Week
# -----------------------------
st.subheader("Trips by Day of Week")

by_day = hourly.groupby("day_of_week", as_index=False, observed=False)["total_rides"].sum()

fig, ax = plt.subplots(figsize=(10, 4))
sns.barplot(data=by_day, x="day_of_week", y="total_rides", ax=ax, color="#4C72B0")
ax.set_xlabel("")
ax.set_ylabel("Number of trips")
st.pyplot(fig, use_container_width=True)
plt.close(fig)

st.write(
    "This chart shows how total trip volume changes across the week. It helps identify which days "
    "have the highest overall demand."
)

# -----------------------------
# Chart 5. Trips by Month / Season
# -----------------------------
st.subheader("Trips by Month / Season")

by_month = (
    monthly.groupby(["month", "month_name"], as_index=False)["total_rides"]
    .sum()
    .sort_values("month")
)

by_month_mc = (
    monthly.groupby(["month", "month_name", "member_casual"], as_index=False)["total_rides"]
    .sum()
    .sort_values("month")
)

season_order = ["Winter", "Spring", "Summer", "Autumn"]
by_season = (
    monthly.groupby("season", as_index=False)["total_rides"]
    .sum()
    .set_index("season")
    .reindex(season_order)
    .dropna()
    .reset_index()
)

col1, col2 = st.columns(2)

with col1:
    fig, ax = plt.subplots(figsize=(7, 4))
    if show_member_split:
        sns.lineplot(
            data=by_month_mc,
            x="month_name",
            y="total_rides",
            hue="member_casual",
            marker="o",
            ax=ax
        )
    sns.lineplot(
        data=by_month,
        x="month_name",
        y="total_rides",
        marker="s",
        ax=ax,
        color="black",
        label="total",
        linewidth=2
    )
    ax.set_title("Trips by Month")
    ax.set_xlabel("")
    ax.set_ylabel("Number of trips")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=30)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

with col2:
    fig, ax = plt.subplots(figsize=(7, 4))
    sns.barplot(data=by_season, x="season", y="total_rides", ax=ax, color="#C44E52")
    ax.set_title("Trips by Season")
    ax.set_xlabel("")
    ax.set_ylabel("Number of trips")
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

st.write(
    "These charts summarize broader time patterns. The monthly chart shows short-term changes over time, "
    "while the seasonal chart groups activity into larger seasonal categories."
)

# -----------------------------
# Chart 6. Hour x Day Heatmap
# -----------------------------
st.subheader("Hour × Day Heatmap")

pivot = (
    hourly.groupby(["day_of_week", "hour"], observed=False)["total_rides"]
    .sum()
    .unstack("hour")
    .reindex(day_order)
)

fig, ax = plt.subplots(figsize=(12, 4))
sns.heatmap(
    pivot,
    cmap="YlOrRd",
    ax=ax,
    cbar_kws={"label": "Number of trips"},
    linewidths=0.3
)
ax.set_xlabel("Hour of day")
ax.set_ylabel("")
st.pyplot(fig, use_container_width=True)
plt.close(fig)

st.write(
    "The heatmap shows how demand changes across both day of week and hour of day at the same time. "
    "It is useful for spotting peak commuting periods and weekend differences."
)

# -----------------------------
# Chart 7. Member vs Casual Usage Pattern
# -----------------------------
st.subheader("Member vs Casual Usage Pattern")

by_hour_mc = hourly.groupby(["hour", "member_casual"], as_index=False)["total_rides"].sum()
by_day_mc = hourly.groupby(["day_of_week", "member_casual"], as_index=False, observed=False)["total_rides"].sum()

col1, col2 = st.columns(2)

with col1:
    fig, ax = plt.subplots(figsize=(7, 4))
    sns.lineplot(
        data=by_hour_mc,
        x="hour",
        y="total_rides",
        hue="member_casual",
        marker="o",
        ax=ax
    )
    ax.set_title("Hourly Pattern by Rider Type")
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Number of trips")
    ax.set_xticks(range(0, 24, 2))
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

with col2:
    fig, ax = plt.subplots(figsize=(7, 4))
    sns.barplot(
        data=by_day_mc,
        x="day_of_week",
        y="total_rides",
        hue="member_casual",
        ax=ax
    )
    ax.set_title("Day of Week by Rider Type")
    ax.set_xlabel("")
    ax.set_ylabel("Number of trips")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=30)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

st.write(
    "These charts compare member and casual riders. They help show whether the two groups follow different "
    "temporal patterns across the day and across the week."
)
