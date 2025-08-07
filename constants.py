ROOT_ID = "a858460b-a291-4b9f-ab25-947b068a4553"
API_KEY = "<YOUR_API_KEY>"
BASE_URL = "<BASE_URL>"
PAGE_SIZE = 1000
MAX_DEPTH = 2
IDIOMS_MAPPING = {
    "Sutsilvan": "rm-sutsilv",
    "Sursilvan": "rm-sursilv",
    "Vallader": "rm-vallader",
    "Surmiran": "rm-surmiran",
    "Puter": "rm-puter",
}
IDIOMS = [
    "rm-sursilv",
    "rm-vallader",
    "rm-puter",
    "rm-surmiran",
    "rm-sutsilv",
]
CONTENT_TYPES_EXCLUDED = [
    "redacziunHome",
    "class",
    "video",
    "pDF",
    "documentTemplate",
    "testCheckExercise",
    "book", #unsure
    "audio", #unsure
    "idiomFolder", #unsure
    "finalTest", #unsure
    "sourcePage", #unsure
    "impressum", #unsure
]
CONTENT_TYPES_INCLUDED = [
    "chapter",
    "exercise",
    "explanation",
    "memo",
    "solution",
    "textimage",
    "topicsPage",
]
CACHE_DIR = "hf_cache"