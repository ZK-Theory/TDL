import yfinance as yf
import pandas as pd

print("Pandas version:", pd.__version__)
print("Yfinance version:", yf.__version__)

vix = yf.download("^VIX", start="2000-01-01", end="2000-01-10", progress=False)
print("Shape:", vix.shape)
print("Columns:", vix.columns)
print("Index Type:", vix.index.dtype)
print("Index Example:", vix.index[:3])
if isinstance(vix.columns, pd.MultiIndex):
    print("MultiIndex Levels:", vix.columns.levels)

print("TRYING ACCESS:")
try:
    c = vix["Close"]
    print("vix['Close'] type:", type(c))
    print("vix['Close'] head:\n", c.head())
except Exception as e:
    print("vix['Close'] failed:", e)

print("TRYING ILOC:")
c2 = vix.iloc[:, 0]
print("vix.iloc[:, 0] type:", type(c2))
print("vix.iloc[:, 0] head:\n", c2.head())
