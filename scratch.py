import pickle
from pathlib import Path
COOKIES_PATH = Path(__file__).parent.absolute().joinpath('cookies.pkl')
cookies = pickle.load(open(COOKIES_PATH, 'rb'))
print(cookies)
