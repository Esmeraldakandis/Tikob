from models import Tradition, db

CULTURAL_TRADITIONS = [
    {
        'name': 'susu',
        'display_name': 'Susu',
        'description': 'Haitian rotating savings and credit association. Members contribute regularly and receive payouts in rotation.',
        'region': 'Haiti, West Africa',
        'cultural_theme': 'haitian',
        'icon': '🇭🇹'
    },
    {
        'name': 'rosca',
        'display_name': 'ROSCA',
        'description': 'Rotating Savings and Credit Association. A traditional savings circle common across Latin America and Africa.',
        'region': 'Latin America, Africa, Asia',
        'cultural_theme': 'global',
        'icon': '🌍'
    },
    {
        'name': 'tanda',
        'display_name': 'Tanda',
        'description': 'Mexican rotating savings group where members pool money and take turns receiving the pot.',
        'region': 'Mexico, Latin America',
        'cultural_theme': 'mexican',
        'icon': '🇲🇽'
    },
    {
        'name': 'chama',
        'display_name': 'Chama',
        'description': 'Kenyan savings group that promotes collective wealth-building and financial literacy.',
        'region': 'Kenya, East Africa',
        'cultural_theme': 'kenyan',
        'icon': '🇰🇪'
    },
    {
        'name': 'pardna',
        'display_name': 'Pardna/Partner',
        'description': 'Jamaican and Caribbean savings circle where members "throw pardna" to build community wealth.',
        'region': 'Jamaica, Caribbean',
        'cultural_theme': 'caribbean',
        'icon': '🇯🇲'
    },
    {
        'name': 'esusu',
        'display_name': 'Esusu',
        'description': 'Nigerian Yoruba savings scheme promoting cooperative economics and mutual aid.',
        'region': 'Nigeria, West Africa',
        'cultural_theme': 'nigerian',
        'icon': '🇳🇬'
    },
    {
        'name': 'stokvels',
        'display_name': 'Stokvel',
        'description': 'South African savings club with roots in community solidarity and economic empowerment.',
        'region': 'South Africa',
        'cultural_theme': 'south_african',
        'icon': '🇿🇦'
    },
    {
        'name': 'hui',
        'display_name': 'Hui',
        'description': 'Chinese rotating credit association used for major purchases and business investments.',
        'region': 'China, Taiwan',
        'cultural_theme': 'chinese',
        'icon': '🇨🇳'
    },
    {
        'name': 'arisan',
        'display_name': 'Arisan',
        'description': 'Indonesian social gathering with lottery-based savings distribution.',
        'region': 'Indonesia',
        'cultural_theme': 'indonesian',
        'icon': '🇮🇩'
    },
    {
        'name': 'custom',
        'display_name': 'Custom Savings Circle',
        'description': 'Create your own savings tradition with personalized rules and cultural elements.',
        'region': 'Global',
        'cultural_theme': 'default',
        'icon': '⚙️',
        'is_custom': True
    }
]

def seed_traditions():
    """Seed the database with predefined cultural savings traditions"""
    for tradition_data in CULTURAL_TRADITIONS:
        existing = Tradition.query.filter_by(name=tradition_data['name']).first()
        if not existing:
            tradition = Tradition(**tradition_data)
            db.session.add(tradition)
    
    db.session.commit()
    print(f"✅ Seeded {len(CULTURAL_TRADITIONS)} cultural savings traditions")

def get_tradition_theme_colors(theme):
    """Return theme-specific color schemes for UI personalization"""
    themes = {
        'haitian': {
            'primary': '#003087',
            'secondary': '#D21034',
            'accent': '#F5A623'
        },
        'mexican': {
            'primary': '#006847',
            'secondary': '#CE1126',
            'accent': '#FFD700'
        },
        'kenyan': {
            'primary': '#BB0000',
            'secondary': '#006600',
            'accent': '#FFFFFF'
        },
        'caribbean': {
            'primary': '#FFB81C',
            'secondary': '#009B3A',
            'accent': '#000000'
        },
        'nigerian': {
            'primary': '#008751',
            'secondary': '#FFFFFF',
            'accent': '#FFD700'
        },
        'south_african': {
            'primary': '#007A3D',
            'secondary': '#FFB81C',
            'accent': '#DE3831'
        },
        'chinese': {
            'primary': '#DE2910',
            'secondary': '#FFDE00',
            'accent': '#C0C0C0'
        },
        'indonesian': {
            'primary': '#FF0000',
            'secondary': '#FFFFFF',
            'accent': '#FFD700'
        },
        'global': {
            'primary': '#1B2A49',
            'secondary': '#D4AF37',
            'accent': '#F5F5DC'
        },
        'default': {
            'primary': '#1B2A49',
            'secondary': '#D4AF37',
            'accent': '#F5F5DC'
        }
    }
    return themes.get(theme, themes['default'])
