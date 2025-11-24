"""
Haitian Cultural Elements
Proverbs, quotes, and financial wisdom from Haitian culture
"""

HAITIAN_PROVERBS = [
    {
        "creole": "Sèl dwèt pa manje kalalou.",
        "english": "One finger alone cannot eat okra.",
        "meaning": "Unity and cooperation are essential for success."
    },
    {
        "creole": "Piti piti zwazo fè nich li.",
        "english": "Little by little, the bird builds its nest.",
        "meaning": "Small, consistent efforts lead to great achievements."
    },
    {
        "creole": "Dèyè mòn gen mòn.",
        "english": "Beyond mountains, there are more mountains.",
        "meaning": "Life's challenges are continuous, but perseverance pays off."
    },
    {
        "creole": "Lè w wè m ap danse, ou pa konnen kote m bouke.",
        "english": "When you see me dancing, you don't know where I'm hurting.",
        "meaning": "People may appear happy despite their struggles."
    },
    {
        "creole": "Men anpil, chay pa lou.",
        "english": "Many hands make the load lighter.",
        "meaning": "Working together makes difficult tasks easier."
    },
    {
        "creole": "Yon jou pou chasè, yon jou pou jibye.",
        "english": "One day for the hunter, one day for the prey.",
        "meaning": "Fortune changes - what goes around comes around."
    },
    {
        "creole": "Bon vwazen pi bon pase fanmi.",
        "english": "A good neighbor is better than distant family.",
        "meaning": "Community support is invaluable."
    },
    {
        "creole": "Travay se richès.",
        "english": "Work is wealth.",
        "meaning": "Hard work is the foundation of prosperity."
    },
    {
        "creole": "Pa vann po chen anvan ou pa touye l.",
        "english": "Don't sell the dog's skin before you kill it.",
        "meaning": "Don't count your chickens before they hatch."
    },
    {
        "creole": "Mache dousman, w ap rivé lwen.",
        "english": "Walk slowly, you'll go far.",
        "meaning": "Patience and persistence lead to success."
    },
    {
        "creole": "Sak vid pa kanpe.",
        "english": "An empty sack cannot stand.",
        "meaning": "You need resources to succeed - save wisely."
    },
    {
        "creole": "Timoun se richès malere.",
        "english": "Children are the wealth of the poor.",
        "meaning": "Family is the greatest treasure."
    },
    {
        "creole": "Lè ou bay, bay san regret.",
        "english": "When you give, give without regret.",
        "meaning": "Generosity should come from the heart."
    },
    {
        "creole": "Pa manje lajan ou poko genyen.",
        "english": "Don't spend money you don't have yet.",
        "meaning": "Live within your means and avoid debt."
    },
    {
        "creole": "Kòb se travay, travay se kòb.",
        "english": "Money is work, work is money.",
        "meaning": "Wealth comes from dedicated effort."
    }
]

FINANCIAL_WISDOM_CREOLE = [
    {
        "creole": "Yon ti kòb chak jou, se gwo richès demen.",
        "english": "A little money each day becomes great wealth tomorrow.",
        "category": "savings"
    },
    {
        "creole": "Sòl pa fè lajan, men li fè bon jaden.",
        "english": "Soil doesn't make money, but it makes a good garden.",
        "meaning": "Invest in sustainable growth.",
        "category": "investment"
    },
    {
        "creole": "Pa prete sa w pa genyen.",
        "english": "Don't lend what you don't have.",
        "category": "debt"
    },
    {
        "creole": "Ekonomize pou jou lapli.",
        "english": "Save for the rainy day.",
        "category": "savings"
    },
    {
        "creole": "Lajan ki nan men w se sèl garanti w genyen.",
        "english": "Money in your hand is your only guarantee.",
        "category": "security"
    },
    {
        "creole": "Dèt se malè.",
        "english": "Debt is misfortune.",
        "category": "debt"
    },
    {
        "creole": "Mete lajan sou kote, pa gaspiye l.",
        "english": "Put money aside, don't waste it.",
        "category": "savings"
    },
    {
        "creole": "Youn ede lòt, Bondye ede tout.",
        "english": "One helps the other, God helps all.",
        "category": "community"
    }
]

COMMUNITY_SAVINGS_PHRASES = {
    "en": {
        "welcome": "Welcome to the circle",
        "contribution": "Your contribution strengthens us all",
        "milestone": "Together we achieve more",
        "encouragement": "Keep building your future",
        "celebration": "Celebrating your success!"
    },
    "ht": {
        "welcome": "Byenveni nan sèk la",
        "contribution": "Kontribisyon w ranfòse nou tout",
        "milestone": "Ansanm nou reyalize plis",
        "encouragement": "Kontinye bati avni w",
        "celebration": "N ap selebre siksè w!"
    }
}

def get_random_proverb(language='en'):
    """Get a random Haitian proverb"""
    import random
    proverb = random.choice(HAITIAN_PROVERBS)
    
    if language == 'ht':
        return {
            'text': proverb['creole'],
            'translation': proverb['english'],
            'meaning': proverb.get('meaning', '')
        }
    else:
        return {
            'text': proverb['english'],
            'original': proverb['creole'],
            'meaning': proverb.get('meaning', '')
        }

def get_financial_wisdom(category=None, language='en'):
    """Get financial wisdom in Creole or English"""
    import random
    
    if category:
        filtered = [w for w in FINANCIAL_WISDOM_CREOLE if w.get('category') == category]
        wisdom = random.choice(filtered) if filtered else random.choice(FINANCIAL_WISDOM_CREOLE)
    else:
        wisdom = random.choice(FINANCIAL_WISDOM_CREOLE)
    
    if language == 'ht':
        return wisdom['creole']
    else:
        return wisdom['english']

def get_community_phrase(key, language='en'):
    """Get a community-related phrase"""
    return COMMUNITY_SAVINGS_PHRASES.get(language, COMMUNITY_SAVINGS_PHRASES['en']).get(key, '')
