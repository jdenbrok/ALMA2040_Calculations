# filename: cost_model.py
from bokeh.io import curdoc
from bokeh.layouts import column, row, Spacer
from bokeh.models import ColumnDataSource, Slider, Div
from bokeh.plotting import figure
import numpy as np
from bokeh.models import CheckboxGroup, CustomJS

# --- Default Parameters (in $) ---
defaults = {
    "C": 50e6,      # base cost
    "f1": 5e6,      # antenna cost factor
    "f2": 2.5e5,    # receiver cost
    "f3": 6000,     # correlator cost
    "SNR": 5,         # collecting area increase
    "alpha":2.7,
    "integrate":[1]
}

# --- Data Preparation Function ---
def compute_costs(C, f1, f2, f3, SNR, integrate, alpha):
    D = np.linspace(6, 50, 300)  # antenna diameters in meters
    D_12m = 12 #current antenna size in m
    n_12m = 50 #current number of antennas
    

    if integrate:
        A_new = (np.pi*D**2/4)
        A_old = (np.pi*D_12m**2/4)

        a = A_new**2
        #b = (n_12m*A_old - 1)*Anew
        b = 2*n_12m*A_old*A_new - A_new**2

        N = n_12m*(n_12m-1)
        #c = N*A_old**2 - SNR**2*(1-0.3)**2 * N * A_old**2
        c = (1-SNR**2*(1-0.3)**2)*N*A_old**2
        n2 = (-b + np.sqrt(b**2-4*a*c))/2/a 

        cost_ant = f1 * n2 * (D / D_12m) ** alpha
        cost_rcv = f2 * n2
        cost_corr = f3 * (n2+n_12m) ** 2
        total_cost = C + cost_ant + cost_rcv + cost_corr

    else:
        c = 2*SNR**2 * (D_12m**2/D**2)**2*(1-0.3)**2 * (n_12m*(n_12m-1)/2)
        n2 = (1+np.sqrt(1+4*c))/2
    
        # Construction cost components
        cost_ant = f1 * n2 * (D / D_12m) ** alpha
        cost_rcv = f2 * n2
        cost_corr = f3 * n2 ** 2
        total_cost = C + cost_ant + cost_rcv + cost_corr

    # Find minimum
    min_index = np.argmin(total_cost)
    D_opt = D[min_index]
    C_min = total_cost[min_index]

    return {
        "D": D,
        "na": n2,
        "cost_ant": cost_ant,
        "cost_rcv": cost_rcv,
        "cost_corr": cost_corr,
        "total_cost": total_cost,
        "D_opt": D_opt,
        "C_min": C_min,
        "new_antennae": int(np.round(n2[min_index]))
    }

# --- Initial Data ---
data = compute_costs(**defaults)
source_left = ColumnDataSource(data=dict(
    D=data["D"],
    total=data["total_cost"],
    ant=data["cost_ant"],
    rcv=data["cost_rcv"],
    corr=data["cost_corr"],
))

# --- Left Plot: Construction Cost ---
p_left = figure(width=700, height=450, title="Construction Cost vs Antenna Diameter (D)", y_axis_type="log")
p_left.line("D", "total", source=source_left, line_width=3, color="navy", legend_label="Total Cost")
p_left.line("D", "ant", source=source_left, line_width=2, color="orange", alpha=0.5, legend_label="Antenna Term")
p_left.line("D", "rcv", source=source_left, line_width=2, color="green", alpha=0.5, legend_label="Receiver Term")
p_left.line("D", "corr", source=source_left, line_width=2, color="red", alpha=0.5, legend_label="Correlator Term")
p_left.legend.location = "top_right"
p_left.xaxis.axis_label = "Antenna Diameter D [m]"
p_left.yaxis.axis_label = "Cost [$] (log scale)"
opt_marker = p_left.circle([data["D_opt"]], [data["C_min"]], size=10, color="black", legend_label="Optimum D")

# --- Parameter Sliders ---

LABEL_checkbox = ["Integrate in Current Array"]


sliders = {
    # C and f1 in million dollars (converted to $ inside callback)
    "C": Slider(title="C (Base Cost) [Million $]", value=defaults["C"]/1e6, start=defaults["C"]/1e7, end=defaults["C"]/1e5, step=0.5),
    "f1": Slider(title="f₁ (Antenna Cost Factor) [Million $]", value=defaults["f1"]/1e6, start=defaults["f1"]/1e7, end=defaults["f1"]/1e5, step=0.1),
    "f2": Slider(title="f₂ (Receiver Cost per Antenna) [$]", value=defaults["f2"], start=defaults["f2"]/10, end=defaults["f2"]*10, step=1e4),
    "f3": Slider(title="f₃ (Correlator Cost Factor) [$]", value=defaults["f3"], start=defaults["f3"]/10, end=defaults["f3"]*10, step=500),
    "SNR": Slider(title="Improvement in (point-source) Line Sensitivity", value=defaults["SNR"], start=1, end=10, step=1),
    "alpha": Slider(title="alpha (Cost-Size Scaling Exponent)", value=defaults["alpha"], start=0, end=4, step=.1),
    "button": CheckboxGroup(labels=LABEL_checkbox, active=[0])
}

# --- Callback ---
def update(attr, old, new):
    # Convert million-dollar sliders to $ again
    values = {
        "C": sliders["C"].value * 1e6,
        "f1": sliders["f1"].value * 1e6,
        "f2": sliders["f2"].value,
        "f3": sliders["f3"].value,
        "SNR": sliders["SNR"].value,
        "alpha": sliders["alpha"].value,
        "integrate": len(sliders["button"].active),
        
    }


    data_new = compute_costs(**values)

    source_left.data = dict(
        D=data_new["D"],
        total=data_new["total_cost"],
        ant=data_new["cost_ant"],
        rcv=data_new["cost_rcv"],
        corr=data_new["cost_corr"],
    )
    opt_marker.data_source.data = dict(x=[data_new["D_opt"]], y=[data_new["C_min"]])
    p_left.title.text = f"Optimum D = {data_new['D_opt']:.2f} m, Cost = {data_new['C_min']/1e9:.2f} B$, #New Antennas = {data_new['new_antennae']}"

for key, s in sliders.items():
    if key == "button":
        s.on_change("active", update)
    else:
        s.on_change("value", update)

# --- Description Text ---
desc = Div(text="""
<h2>Telescope Cost Model</h2>
<p>
This interactive tool illustrates the trade-offs in designing an interferometric array by linking 
antenna diameter <i>D</i>, number of antennas <i>n<sub>a</sub></i>, and total construction cost.
</p>

<h3>Construction Cost Function</h3>
<p style="font-family: monospace;">
C<sub>total</sub> = C + f<sub>1</sub>·n<sub>a</sub>·(D/12)<sup>alpha</sup> + f<sub>2</sub>·n<sub>a</sub> + f<sub>3</sub>·n<sub>a</sub><sup>2</sup>
</p>
<p>
where the number of antennas depends on the degree of SNR improvement.

<ul>
<li><b>C</b> – fixed base cost (Million $)</li>
<li><b>f₁</b> – antenna construction cost scaling ∝ D<sup>2.7</sup> (Million $)</li>
<li><b>f₂</b> – receiver system cost per antenna ($)</li>
<li><b>f₃</b> – correlator cost scaling ∝ n<sub>a</sub><sup>2</sup> ($)</li>
<li><b>SNR</b> – Improvement in (point-source) Line Sensitivity</li>
</ul>

<p>
The figure below shows the construction cost as a function of antenna diameter <i>D</i>, 
highlighting individual contributions and marking the configuration that minimizes total cost.
</p>
""", width=1200)

# --- Layout ---
layout = column(
    desc,
    row(p_left, Spacer(width=50), column(*sliders.values(), spacing=15))
)

curdoc().add_root(layout)
curdoc().title = "Cost Model"