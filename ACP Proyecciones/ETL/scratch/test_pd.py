import pandas as pd
import numpy as np
df = pd.DataFrame({'a': [1, np.nan, 3], 'b': ['x', None, 'z']})
df = df.replace({np.nan: None})
for r in df.to_dict('records'):
    print(r)
