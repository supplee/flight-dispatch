# 
# Convert NoSQL parquet data to SQL tables... SQL is slower but I'd like the practice writing complex queries!
#

import pandas as pd
from sqlalchemy import create_engine

df = pd.read_parquet('airportposition.parquet.gzip')
df.columns = [c.lower() for c in df.columns] # postgres doesn't like capitals accordfing to Moein Hossein!
try:
    df=df.assign(airport_id = lambda x: x['rec #.'])
    df=df.drop('rec #.',axis=1)
    df=df.drop('id',axis=1)
except:
    print("ERROR CHANGING KEY COLUMN ID")

engine = create_engine('sqlite:///data.db', echo=True)
df.to_sql('airport', engine, if_exists='append', index=False)


