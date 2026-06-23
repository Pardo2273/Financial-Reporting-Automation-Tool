import tkinter as tk
from tkinter import filedialog
import pandas as pd
import threading
import os

#FUNTIONS TO TRANSFOR THE REPORT BEGIN  HERE #

# beacuse we delimited the file types in the file dialog, we can be sure that the file is either an excel or a csv, so we can read it with the corresponding function
def read_file(file):
    if file.endswith('.xlsx') or file.endswith('.xls'):
        return pd.read_excel(file)
    else:
        return pd.read_csv(file)
    
def change_comma_to_dot(value):
    if isinstance(value, str):
        return value.replace(',', '.')
    return value

# this funtion is only to remove all the dots except the decimal one, this is because in some countries, the dot is used as a thousand separator, so we need to remove it before we can convert the string to a float
def remove_dot(value):
    las_dot= value.rfind('.') # find the last dot in the string, this is the decimal separator -> if it doesn't find any dot, it will return -1
    if las_dot != -1:
        integer_part = value.replace('.','')[:las_dot]
        decimal_part = value[las_dot:]
        return integer_part + decimal_part
    return value

def apply_dot(array, df):
    array= [value.apply(change_comma_to_dot) for value in array]
    array= [value.apply(remove_dot) for value in array]
    array = [value.apply(pd.to_numeric) for value in array]
    df['monthly_payment'] = array[0]
    df['annual_payment'] = array[1]
    df['other_payment'] = array[2]
    df['iva_amount'] = array[3]
    df['total_amount'] = array[4]
    df['late_penalty'] = array[5]
    return df

# This function avoid to have rows with all the values in zero or work with negative values, because in the financial report, we only want to work with rows that have at least one positive value, this way we can avoid to have rows that are not relevant for our analysis
def all_no_zero_values(df):
    df = df[(df['monthly_payment'] > 0) | (df['annual_payment'] > 0) | (df['other_payment'] > 0) | (df['iva_amount'] > 0) | (df['total_amount'] > 0) | (df['late_penalty'] > 0)]
    return df

def change_currency(value):
    value= value.capitalize() # we capitalize the first letter of the string, this way we can avoid to have problems with the case sensitivity, for example, if the value is "dólares" or "DÓLARES", it will be converted to "Dólares" and then we can compare it with the string "Dólares" without any problem
    if 'Dólares' in value:
        return 'USD'
    elif 'Euros' in value:
        return 'EUR'
    elif 'Colones' in value:
        return 'CRC'
    else:
        return value

def build_full_name(df):
    df['full_name'] = df['first_name'] + ' ' + df['last_name']
    df['full_name'] = df['full_name'].str.title()
    df.drop(['first_name', 'last_name'], axis=1, inplace=True)
    return df

def format_date(df):
    df['purchase_date'] = pd.to_datetime(df['purchase_date'])
    df['purchase_date'] = df['purchase_date'].dt.strftime('%Y-%m-%d')
    return df

# this tax rate is in percentage, so we need to remove the percentage sign and convert it to a decimal number, for example, if the tax rate is "13%", we need to convert it to 0.13
def format_iva(df):
    df['iva_rate'] = df['iva_rate'].str.replace('%', '')
    df['iva_rate'] = pd.to_numeric(df['iva_rate'])
    df['iva_rate'] = df['iva_rate'] / 100
    return df

def clasify_purchases(df):
    df['purchase_type'] = ''
    df['Penalization'] = False
    df.loc[df['monthly_payment'] > 0, 'purchase_type'] = 'Monthly'
    df.loc[df['annual_payment'] > 0, 'purchase_type'] = 'Annual'
    df.loc[df['other_payment'] > 0, 'purchase_type'] = 'Non-Recurring'
    df.loc[df['late_penalty'] > 0, 'Penalization'] = True
    return df

#usign str slicing to clean the purchase number and customer id
def clean_identifiers(df): 
    df['purchase_number']= df['purchase_number'].str[4:]
    df['customer_id'] = df['customer_id'].str[3:]
    return df

def transform_report(file_path):
    data = read_file(file_path)

    # We make a copy of the original dataframe to work with it and avoid modifying the original data, this way we can always go back to the original data if we need to
    df = data.copy()

    array_ = [df['monthly_payment'], df['annual_payment'], df['other_payment'], df['iva_amount'], df['total_amount'], df['late_penalty']]

    df= apply_dot(array_, df)

    df = all_no_zero_values(df)

    df['currency'] = df['currency'].apply(change_currency)

    df = build_full_name(df)

    df = format_date(df)

    df = format_iva(df)

    df = clasify_purchases(df)

    df = clean_identifiers(df)

    df = df[['purchase_number', 'customer_id', 'full_name', 'purchase_date', 'branch', 'transaction_type', 'currency', 'monthly_payment', 
         'annual_payment', 'other_payment', 'purchase_type', 'iva_rate', 'iva_amount', 'total_amount', 'Penalization', 'late_penalty']]

    downloads    = os.path.join(os.path.expanduser("~"), "Downloads")
    output_path  = os.path.join(downloads, "financial_report.xlsx")

    df.to_excel(output_path, index=False)


# ALL ABOUT THE USER INTERFACE BEGIN HERE #
# ---------- Colors ----------
BG= "#F0F2F5"
CARD_BG= "#FFFFFF"
PRIMARY= "#1C2B3A"
PRIMARY_H= "#2E4057"
TEXT_DARK= "#1A1A2E"
TEXT_MUTED= "#6C757D"
ACCENT= "#0D6EFD"
SUCCESS= "#198754"
DANGER= "#DC3545"
DISABLED= "#CED4DA"
BORDER= "#DEE2E6"

selected_file_path = None
 
# ──────────────────────────────────────────────────────
#  CANVAS SPINNER
# ──────────────────────────────────────────────────────
_arc_angle  = 0
_spinner_job = None

def _draw_arc():
    global _arc_angle, _spinner_job
    spinner_canvas.delete("arc")
    size   = 54
    pad    = 6
    start  = _arc_angle % 360
    # track (grey ring)
    spinner_canvas.create_arc(
        pad, pad, size - pad, size - pad,
        start=0, extent=359,
        style="arc", outline=BORDER, width=5, tags="arc"
    )
    # moving arc (blue)
    spinner_canvas.create_arc(
        pad, pad, size - pad, size - pad,
        start=start, extent=90,
        style="arc", outline=ACCENT, width=5, tags="arc"
    )
    _arc_angle -= 8
    _spinner_job = root.after(30, _draw_arc)

def start_spinner():
    spinner_canvas.place(relx=0.5, rely=0.42, anchor="center")
    _draw_arc()

def stop_spinner():
    global _spinner_job
    if _spinner_job:
        root.after_cancel(_spinner_job)
        _spinner_job = None
    spinner_canvas.place_forget()
    spinner_canvas.delete("arc")

# ──────────────────────────────────────────────────────
#  OVERLAY
# ──────────────────────────────────────────────────────
def show_overlay(message: str):
    overlay_label.config(text=message)
    overlay.lift()
    overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
    start_spinner()

def hide_overlay():
    stop_spinner()
    overlay.place_forget()

# ──────────────────────────────────────────────────────
#  BUTTON STATE
# ──────────────────────────────────────────────────────
def set_btn(btn, enabled: bool, color=None):
    if enabled:
        c = color or PRIMARY
        btn.config(state="normal", bg=c, fg="#FFFFFF", cursor="hand2")
    else:
        btn.config(state="disabled", bg=DISABLED, fg="#FFFFFF", cursor="")

# ──────────────────────────────────────────────────────
#  FILE SELECTION
# ──────────────────────────────────────────────────────
def select_file():
    global selected_file_path
    path = filedialog.askopenfilename(
        title="Select a file to transform",
        filetypes=[("Excel / CSV files", "*.xlsx *.xls *.csv")],
    )
    if path:
        selected_file_path = path
        filename = os.path.basename(path)
        file_label.config(text=f"📄  {filename}", fg=TEXT_DARK, font=("Segoe UI", 11, "bold"))
        status_dot.config(fg=SUCCESS)
        status_text.config(text="File ready — you're good to go", fg=SUCCESS)
        select_btn.config(text="Change file")
        set_btn(report_btn, True, SUCCESS)
    else:
        if not selected_file_path:
            status_dot.config(fg=DANGER)
            status_text.config(text="No file selected", fg=TEXT_MUTED)

# ──────────────────────────────────────────────────────
#  REPORT GENERATION
# ──────────────────────────────────────────────────────
def make_report():
    set_btn(select_btn, False)
    set_btn(report_btn, False)
    show_overlay("Generating your report…")

    def worker():
        try:
            transform_report(selected_file_path)
            root.after(0, on_success)
        except Exception as exc:
            root.after(0, lambda: on_error(str(exc)))

    threading.Thread(target=worker, daemon=True).start()

def on_success():
    stop_spinner()
    # Green checkmark message
    overlay_label.config(
        text="✅  Report saved to your Downloads folder.\n\nClosing in 3 seconds…",
        fg=SUCCESS,
    )
    root.after(3000, root.destroy)

def on_error(msg: str):
    hide_overlay()
    status_dot.config(fg=DANGER)
    status_text.config(text=f"Error: {msg}", fg=DANGER)
    set_btn(select_btn, True)
    set_btn(report_btn, True, SUCCESS)

# ──────────────────────────────────────────────────────
#  WINDOW
# ──────────────────────────────────────────────────────
root = tk.Tk()
root.state("zoomed")
root.config(bg=BG)
root.title("Financial Reporting Automation Tool")

# ── Header ────────────────────────────────────────────
header = tk.Frame(root, bg=PRIMARY, height=72)
header.pack(fill="x", side="top")
header.pack_propagate(False)

tk.Label(
    header,
    text="📊  Financial Reporting Automation Tool",
    font=("Segoe UI", 16, "bold"),
    fg="#FFFFFF", bg=PRIMARY,
).pack(side="left", padx=32, pady=18)

# ── Content ───────────────────────────────────────────
content = tk.Frame(root, bg=BG)
content.pack(expand=True, fill="both")

# Drop-shadow illusion via a slightly-offset dark frame
shadow = tk.Frame(content, bg="#C8CDD3")
shadow.place(relx=0.5, rely=0.455, anchor="center", width=666, height=446)

card = tk.Frame(shadow, bg=CARD_BG, bd=0)
card.place(x=0, y=0, width=662, height=442)

# ── Card content ──────────────────────────────────────
tk.Label(
    card,
    text="Generate your financial report",
    font=("Segoe UI", 21, "bold"),
    fg=TEXT_DARK, bg=CARD_BG,
).pack(pady=(44, 4))

tk.Label(
    card,
    text="Select an Excel or CSV file and click  Make the Report.",
    font=("Segoe UI", 11),
    fg=TEXT_MUTED, bg=CARD_BG,
).pack(pady=(0, 6))

# Thin divider
tk.Frame(card, bg=BORDER, height=1).pack(fill="x", padx=40, pady=(10, 22))

# File name
file_label = tk.Label(
    card,
    text="No file selected yet",
    font=("Segoe UI", 11, "italic"),
    fg=TEXT_MUTED, bg=CARD_BG,
)
file_label.pack(pady=(0, 16))

# Status row
status_row = tk.Frame(card, bg=CARD_BG)
status_row.pack(pady=(0, 28))

status_dot = tk.Label(status_row, text="●", font=("Segoe UI", 13), fg=DANGER, bg=CARD_BG)
status_dot.pack(side="left", padx=(0, 6))

status_text = tk.Label(
    status_row,
    text="No file selected",
    font=("Segoe UI", 11),
    fg=TEXT_MUTED, bg=CARD_BG,
)
status_text.pack(side="left")

# Buttons
btn_row = tk.Frame(card, bg=CARD_BG)
btn_row.pack()

select_btn = tk.Button(
    btn_row, text="Select file", command=select_file,
    font=("Segoe UI", 12, "bold"), fg="#FFFFFF", bg=PRIMARY,
    activebackground=PRIMARY_H, activeforeground="#FFFFFF",
    width=18, height=2, bd=0, relief="flat", cursor="hand2",
)
select_btn.pack(side="left", padx=(0, 14))
select_btn.bind("<Enter>", lambda e: select_btn.config(bg=PRIMARY_H) if select_btn["state"] == "normal" else None)
select_btn.bind("<Leave>", lambda e: select_btn.config(bg=PRIMARY)   if select_btn["state"] == "normal" else None)

report_btn = tk.Button(
    btn_row, text="Make the Report", command=make_report,
    font=("Segoe UI", 12, "bold"), fg="#FFFFFF", bg=DISABLED,
    activebackground="#157347", activeforeground="#FFFFFF",
    width=18, height=2, bd=0, relief="flat", cursor="", state="disabled",
)
report_btn.pack(side="left")
report_btn.bind("<Enter>", lambda e: report_btn.config(bg="#157347") if report_btn["state"] == "normal" else None)
report_btn.bind("<Leave>", lambda e: report_btn.config(bg=SUCCESS)   if report_btn["state"] == "normal" else None)

# ── Loading overlay ───────────────────────────────────
overlay = tk.Frame(card, bg=CARD_BG)

# Canvas spinner (54×54 px)
spinner_canvas = tk.Canvas(overlay, width=54, height=54, bg=CARD_BG, highlightthickness=0)

overlay_label = tk.Label(
    overlay,
    text="",
    font=("Segoe UI", 14, "bold"),
    fg=TEXT_DARK, bg=CARD_BG,
    justify="center",
)
overlay_label.place(relx=0.5, rely=0.62, anchor="center")

# ── Footer ────────────────────────────────────────────
tk.Label(
    root,
    text="v1.0  —  Tool developed by Gabriel Prado",
    font=("Segoe UI", 9),
    fg=TEXT_MUTED, bg=BG,
).pack(side="bottom", pady=10)

root.mainloop()