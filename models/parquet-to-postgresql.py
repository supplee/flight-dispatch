# 
# Convert NoSQL parquet data to SQL tables... SQL is slower but I'd like the practice writing complex queries!
#

import pandas as pd
from sqlalchemy import create_engine

df = pd.read_parquet('aircraftspeed.parquet')
df.columns = [c.lower() for c in df.columns] # postgres doesn't like capitals accordfing to Moein Hossein!

engine = create_engine('postgresql://dispatch:dispatchPassword@localhost:5432', echo=True)
df.to_sql('aircraft', engine)


