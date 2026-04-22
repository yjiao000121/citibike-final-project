import streamlit as st
import pandas as pd
import networkx as nx
import plotly.express as px
import plotly.graph_objects as go

st.title("Section 3. Network Analysis")
st.write(
    "This page examines Citi Bike station connectivity in the Jersey City–Hoboken area "
    "using trip data from January to March 2025."
)

# -----------------------------
# Load data
# -----------------------------
@st.cache_data
def load_data():
    return pd.read_csv("data/od_edges.csv")

od = load_data()

# -----------------------------
# Sidebar filters
# -----------------------------
st.sidebar.header("Interactive Filters")

top_pair_n = st.sidebar.slider(
    "Top routes to show",
    min_value=5,
    max_value=20,
    value=10,
    step=1
)

top_station_n = st.sidebar.slider(
    "Top stations to show",
    min_value=5,
    max_value=15,
    value=10,
    step=1
)

top_n_edges = st.sidebar.slider(
    "Network map: top edges",
    min_value=10,
    max_value=50,
    value=30,
    step=5
)

min_trip_value = int(od["trip_count"].min())
max_trip_value = int(od["trip_count"].max())

default_min_trips = 300
if default_min_trips > max_trip_value:
    default_min_trips = min_trip_value

min_trips = st.sidebar.slider(
    "Minimum trips for network map",
    min_value=min_trip_value,
    max_value=max_trip_value,
    value=default_min_trips,
    step=10 if max_trip_value >= 100 else 1
)

# -----------------------------
# 1. Top Station-to-Station Flows
# -----------------------------
st.subheader("Top Station-to-Station Flows")

od_pairs = od.copy()
od_pairs["route"] = od_pairs["start_station_name"] + " → " + od_pairs["end_station_name"]
top_pairs = od_pairs.sort_values("trip_count", ascending=False).head(top_pair_n)

fig_pairs = px.bar(
    top_pairs.sort_values("trip_count", ascending=True),
    x="trip_count",
    y="route",
    orientation="h",
    title=f"Top {top_pair_n} Station-to-Station Flows",
    labels={"trip_count": "Number of Trips", "route": "Station Pair"},
    height=500
)

fig_pairs.update_traces(marker_color="#636EFA")
fig_pairs.update_layout(template="plotly")

st.plotly_chart(fig_pairs, use_container_width=True)

st.write(
    "The strongest flows are concentrated among a small number of specific station-to-station routes. "
    "Major corridors appear around Grove St PATH, Liberty Light Rail, and McGinley Square, "
    "suggesting repeated movement between important mobility nodes."
)

# -----------------------------
# 2. Top Most Connected Stations
# -----------------------------
st.subheader("Top Most Connected Stations")

outflow = (
    od.groupby(["start_station_name", "start_station_id"], as_index=False)
    .agg(outflow=("trip_count", "sum"))
    .rename(columns={
        "start_station_name": "station_name",
        "start_station_id": "station_id"
    })
)

inflow = (
    od.groupby(["end_station_name", "end_station_id"], as_index=False)
    .agg(inflow=("trip_count", "sum"))
    .rename(columns={
        "end_station_name": "station_name",
        "end_station_id": "station_id"
    })
)

station_flow = pd.merge(
    outflow, inflow,
    on=["station_name", "station_id"],
    how="outer"
).fillna(0)

station_flow["total_flow"] = station_flow["outflow"] + station_flow["inflow"]

top_stations = station_flow.sort_values("total_flow", ascending=False).head(top_station_n)

fig_stations = px.bar(
    top_stations.sort_values("total_flow", ascending=True),
    x="total_flow",
    y="station_name",
    orientation="h",
    title=f"Top {top_station_n} Most Connected Stations",
    labels={"total_flow": "Total Flow (In + Out)", "station_name": "Station"},
    height=500
)

fig_stations.update_traces(marker_color="#636EFA")
fig_stations.update_layout(template="plotly")

st.plotly_chart(fig_stations, use_container_width=True)

st.write(
    "Grove St PATH and Hoboken Terminal - River St & Hudson Pl appear to be the most active stations "
    "when total incoming and outgoing trips are combined. This suggests that Citi Bike activity is concentrated "
    "around a small number of hub locations."
)

# -----------------------------
# 3. Filtered Network Map
# -----------------------------
st.subheader("Filtered Station Network on Map")

filtered_edges = od[od["trip_count"] >= min_trips].copy()
top_edges = filtered_edges.sort_values("trip_count", ascending=False).head(top_n_edges).copy()

if top_edges.empty:
    st.warning("No edges match the current filter settings. Lower the minimum trip threshold.")
else:
    fig_map = go.Figure()
    max_weight = top_edges["trip_count"].max()

    for _, row in top_edges.iterrows():
        line_width = 1 + 8 * (row["trip_count"] / max_weight)

        fig_map.add_trace(
            go.Scattermapbox(
                mode="lines",
                lon=[row["start_lng"], row["end_lng"]],
                lat=[row["start_lat"], row["end_lat"]],
                line=dict(width=line_width, color="rgba(200, 50, 50, 0.45)"),
                hoverinfo="text",
                text=f"{row['start_station_name']} → {row['end_station_name']}<br>Trips: {row['trip_count']}",
                showlegend=False
            )
        )

    node_sizes_dict = station_flow.set_index("station_name")["total_flow"].to_dict()
    max_node_flow = station_flow["total_flow"].max()

    nodes_in_top = set(top_edges["start_station_name"]).union(set(top_edges["end_station_name"]))

    node_lon = []
    node_lat = []
    node_text = []
    node_size = []

    for station in nodes_in_top:
        start_match = top_edges[top_edges["start_station_name"] == station]
        end_match = top_edges[top_edges["end_station_name"] == station]

        if not start_match.empty:
            lon = start_match.iloc[0]["start_lng"]
            lat = start_match.iloc[0]["start_lat"]
        else:
            lon = end_match.iloc[0]["end_lng"]
            lat = end_match.iloc[0]["end_lat"]

        node_lon.append(lon)
        node_lat.append(lat)
        node_text.append(f"{station}<br>Total flow: {node_sizes_dict.get(station, 0):,.0f}")
        node_size.append(8 + 22 * (node_sizes_dict.get(station, 0) / max_node_flow))

    fig_map.add_trace(
        go.Scattermapbox(
            mode="markers",
            lon=node_lon,
            lat=node_lat,
            marker=dict(size=node_size, color="royalblue", opacity=0.8),
            text=node_text,
            hoverinfo="text",
            showlegend=False
        )
    )

    fig_map.update_layout(
        title=f"Filtered Citi Bike Station Network on Map (Top {top_n_edges} Flows, Min {min_trips} Trips)",
        mapbox=dict(
            style="carto-positron",
            center=dict(lat=40.725, lon=-74.045),
            zoom=12.2
        ),
        margin=dict(l=20, r=20, t=60, b=20),
        height=750
    )

    st.plotly_chart(fig_map, use_container_width=True)

st.write(
    "The filtered network map shows that the strongest Citi Bike connections are concentrated around a few key hubs, "
    "especially Grove St PATH, Hoboken Terminal, and nearby transit-linked stations. "
    "This suggests strong local clustering rather than a uniform network."
)

# -----------------------------
# Adjacency Matrix Heatmap
# -----------------------------
st.subheader("Adjacency Matrix Heatmap")

matrix_top_n = st.sidebar.slider(
    "Heatmap: top stations",
    min_value=5,
    max_value=15,
    value=10,
    step=1
)

top_station_list = (
    station_flow.sort_values("total_flow", ascending=False)
    .head(matrix_top_n)["station_name"]
    .tolist()
)

matrix_df = od[
    od["start_station_name"].isin(top_station_list) &
    od["end_station_name"].isin(top_station_list)
].copy()

adj_matrix = (
    matrix_df.pivot_table(
        index="start_station_name",
        columns="end_station_name",
        values="trip_count",
        aggfunc="sum",
        fill_value=0
    )
    .reindex(index=top_station_list, columns=top_station_list, fill_value=0)
)

label_map = {
    "Hoboken Terminal - River St & Hudson Pl": "Hoboken Terminal (River St)",
    "Hoboken Terminal - Hudson St & Hudson Pl": "Hoboken Terminal (Hudson St)",
    "City Hall - Washington St & 1 St": "City Hall",
    "8 St & Washington St": "8 St & Washington",
    "River St & 1 St": "River St & 1 St"
}

short_index = [label_map.get(x, x) for x in adj_matrix.index]
short_cols = [label_map.get(x, x) for x in adj_matrix.columns]

fig_matrix = px.imshow(
    adj_matrix,
    labels=dict(x="Destination Station", y="Origin Station", color="Trips"),
    x=short_cols,
    y=short_index,
    color_continuous_scale="YlOrRd",
    title=f"Adjacency Matrix of Top {matrix_top_n} Stations"
)

fig_matrix.update_xaxes(
    tickangle=45,
    automargin=True,
    tickfont=dict(size=10)
)

fig_matrix.update_yaxes(
    tickangle=0,
    automargin=True,
    tickfont=dict(size=10)
)

fig_matrix.update_layout(
    height=700,
    margin=dict(l=220, r=40, t=60, b=160)
)

st.plotly_chart(fig_matrix, use_container_width=True)

st.write(
    "This heatmap shows trip volume between the most active stations in the network. "
    "Darker cells indicate stronger station-to-station connections, making pairwise relationships "
    "easier to compare than in a crowded network graph."
)
