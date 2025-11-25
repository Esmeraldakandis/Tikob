"""
AI Service for TiKòb - Real-time Proverb Generation and Translation
Uses Replit AI Integrations (Gemini) - no API key required, charges billed to credits
"""

import os
import json
import random
from typing import Optional
from functools import lru_cache

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

AI_INTEGRATIONS_GEMINI_API_KEY = os.environ.get("AI_INTEGRATIONS_GEMINI_API_KEY")
AI_INTEGRATIONS_GEMINI_BASE_URL = os.environ.get("AI_INTEGRATIONS_GEMINI_BASE_URL")

client = None
if AI_INTEGRATIONS_GEMINI_API_KEY and AI_INTEGRATIONS_GEMINI_BASE_URL:
    try:
        client = genai.Client(
            api_key=AI_INTEGRATIONS_GEMINI_API_KEY,
            http_options={
                'api_version': '',
                'base_url': AI_INTEGRATIONS_GEMINI_BASE_URL   
            }
        )
    except Exception as e:
        print(f"Note: Gemini AI client not initialized: {e}")

SUPPORTED_LANGUAGES = {
    'en': 'English',
    'ht': 'Haitian Creole',
    'es': 'Spanish',
    'fr': 'French',
    'pt': 'Portuguese',
    'ar': 'Arabic',
    'zh': 'Chinese (Simplified)',
    'hi': 'Hindi',
    'ja': 'Japanese',
    'ko': 'Korean',
    'ru': 'Russian',
    'de': 'German'
}

LANGUAGE_FLAGS = {
    'en': '🇺🇸',
    'ht': '🇭🇹',
    'es': '🇪🇸',
    'fr': '🇫🇷',
    'pt': '🇧🇷',
    'ar': '🇸🇦',
    'zh': '🇨🇳',
    'hi': '🇮🇳',
    'ja': '🇯🇵',
    'ko': '🇰🇷',
    'ru': '🇷🇺',
    'de': '🇩🇪'
}

def is_rate_limit_error(exception: BaseException) -> bool:
    """Check if the exception is a rate limit or quota violation error."""
    error_msg = str(exception)
    return (
        "429" in error_msg 
        or "RATELIMIT_EXCEEDED" in error_msg
        or "quota" in error_msg.lower() 
        or "rate limit" in error_msg.lower()
        or (hasattr(exception, 'status') and getattr(exception, 'status', None) == 429)
    )


def generate_haitian_proverb() -> dict:
    """
    Generate a new authentic Haitian proverb in real-time using AI.
    Returns proverb in Haitian Creole with English translation and meaning.
    """
    if not client:
        return get_fallback_proverb()
    
    prompt = """You are a cultural expert on Haitian traditions and wisdom. Generate ONE new, original Haitian proverb that sounds authentic and follows the traditional style of Haitian proverbs.

The proverb should:
- Be about community, savings, unity, hard work, perseverance, or family - themes relevant to community savings groups
- Sound natural in Haitian Creole (not a direct translation from English)
- Have the rhythm and wisdom style of traditional Haitian proverbs
- Be concise (usually 5-12 words in Creole)

Return ONLY valid JSON in this exact format (no other text):
{
    "creole": "The proverb in authentic Haitian Creole",
    "english": "The English translation",
    "meaning": "A brief explanation of its wisdom (1-2 sentences)"
}"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        result = json.loads(response.text or "{}")
        
        if 'creole' in result and 'english' in result:
            return {
                'creole': result['creole'],
                'english': result['english'],
                'meaning': result.get('meaning', '')
            }
    except Exception as e:
        print(f"AI proverb generation failed: {e}")
    
    return get_fallback_proverb()


def get_fallback_proverb() -> dict:
    """Return a fallback proverb if AI generation fails."""
    fallback_proverbs = [
        {
            "creole": "Ansanm nou fò, separe nou fèb",
            "english": "Together we are strong, apart we are weak",
            "meaning": "Unity brings strength to the community"
        },
        {
            "creole": "Lajan pa fèt nan yon jou",
            "english": "Money isn't made in a day",
            "meaning": "Wealth building requires patience and time"
        },
        {
            "creole": "Kote ki gen kè, gen chemen",
            "english": "Where there is heart, there is a way",
            "meaning": "Determination overcomes all obstacles"
        },
        {
            "creole": "Pitit piti, kay monte",
            "english": "Little by little, the house gets built",
            "meaning": "Small consistent efforts lead to great achievements"
        },
        {
            "creole": "Men anpil, chay pa lou",
            "english": "Many hands make the load lighter",
            "meaning": "Working together makes difficult tasks easier"
        }
    ]
    return random.choice(fallback_proverbs)


def translate_text(text: str, target_language: str) -> str:
    """
    Translate text to the target language with cultural accuracy.
    Uses AI for nuanced, contextual translations.
    """
    if target_language not in SUPPORTED_LANGUAGES:
        return text
    
    if target_language == 'en':
        return text
    
    if not client:
        return text
    
    language_name = SUPPORTED_LANGUAGES[target_language]
    
    prompt = f"""Translate the following text to {language_name}. 
This is for a community savings application called TiKòb. 
Ensure the translation is:
- Culturally appropriate and natural-sounding
- Accurate in meaning (not a literal word-for-word translation)
- Uses common, accessible vocabulary

Text to translate: "{text}"

Return ONLY the translated text, nothing else."""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text.strip().strip('"') if response.text else text
    except Exception as e:
        print(f"Translation failed: {e}")
        return text


UI_TRANSLATIONS = {
    'en': {
        'welcome': 'Welcome',
        'login': 'Login',
        'signup': 'Sign Up',
        'logout': 'Logout',
        'dashboard': 'Dashboard',
        'my_groups': 'My Groups',
        'create_group': 'Create Group',
        'join_group': 'Join Group',
        'settings': 'Settings',
        'profile': 'Profile',
        'community_savings': 'Community Savings Made Simple',
        'username': 'Username',
        'password': 'Password',
        'email': 'Email',
        'enter_username': 'Enter your username',
        'enter_password': 'Enter your password',
        'enter_email': 'Enter your email',
        'dont_have_account': "Don't have an account?",
        'already_have_account': 'Already have an account?',
        'create_account': 'Create Account',
        'start_journey': 'Start your savings journey today',
        'many_hands': 'Many hands make the load lighter',
        'together_stronger': 'Together we are stronger',
        'groups': 'Groups',
        'members': 'Members',
        'total_saved': 'Total Saved',
        'contribution': 'Contribution',
        'next_payout': 'Next Payout',
        'view_group': 'View Group',
        'admin': 'Admin',
        'member': 'Member'
    },
    'ht': {
        'welcome': 'Byenveni',
        'login': 'Konekte',
        'signup': 'Enskri',
        'logout': 'Dekonekte',
        'dashboard': 'Tablo',
        'my_groups': 'Gwoup Mwen',
        'create_group': 'Kreye Gwoup',
        'join_group': 'Antre nan Gwoup',
        'settings': 'Paramèt',
        'profile': 'Pwofil',
        'community_savings': 'Ekonomi Kominote, Senp e Fasil',
        'username': 'Non Itilizatè',
        'password': 'Modpas',
        'email': 'Imèl',
        'enter_username': 'Antre non ou',
        'enter_password': 'Antre modpas ou',
        'enter_email': 'Antre imèl ou',
        'dont_have_account': 'Pa gen kont?',
        'already_have_account': 'Deja gen kont?',
        'create_account': 'Kreye Kont',
        'start_journey': 'Kòmanse vwayaj ekonomi ou jodi a',
        'many_hands': 'Men anpil, chay pa lou',
        'together_stronger': 'Ansanm nou pi fò',
        'groups': 'Gwoup',
        'members': 'Manm',
        'total_saved': 'Total Ekonomize',
        'contribution': 'Kontribisyon',
        'next_payout': 'Pwochen Peyman',
        'view_group': 'Wè Gwoup',
        'admin': 'Admin',
        'member': 'Manm'
    },
    'es': {
        'welcome': 'Bienvenido',
        'login': 'Iniciar Sesión',
        'signup': 'Registrarse',
        'logout': 'Cerrar Sesión',
        'dashboard': 'Panel',
        'my_groups': 'Mis Grupos',
        'create_group': 'Crear Grupo',
        'join_group': 'Unirse a Grupo',
        'settings': 'Configuración',
        'profile': 'Perfil',
        'community_savings': 'Ahorro Comunitario Simplificado',
        'username': 'Usuario',
        'password': 'Contraseña',
        'email': 'Correo',
        'enter_username': 'Ingresa tu usuario',
        'enter_password': 'Ingresa tu contraseña',
        'enter_email': 'Ingresa tu correo',
        'dont_have_account': '¿No tienes cuenta?',
        'already_have_account': '¿Ya tienes cuenta?',
        'create_account': 'Crear Cuenta',
        'start_journey': 'Comienza tu viaje de ahorro hoy',
        'many_hands': 'Muchas manos alivian el trabajo',
        'together_stronger': 'Juntos somos más fuertes',
        'groups': 'Grupos',
        'members': 'Miembros',
        'total_saved': 'Total Ahorrado',
        'contribution': 'Contribución',
        'next_payout': 'Próximo Pago',
        'view_group': 'Ver Grupo',
        'admin': 'Admin',
        'member': 'Miembro'
    },
    'fr': {
        'welcome': 'Bienvenue',
        'login': 'Connexion',
        'signup': "S'inscrire",
        'logout': 'Déconnexion',
        'dashboard': 'Tableau de Bord',
        'my_groups': 'Mes Groupes',
        'create_group': 'Créer un Groupe',
        'join_group': 'Rejoindre un Groupe',
        'settings': 'Paramètres',
        'profile': 'Profil',
        'community_savings': "L'Épargne Communautaire Simplifiée",
        'username': "Nom d'utilisateur",
        'password': 'Mot de passe',
        'email': 'Email',
        'enter_username': 'Entrez votre nom',
        'enter_password': 'Entrez votre mot de passe',
        'enter_email': 'Entrez votre email',
        'dont_have_account': "Pas de compte?",
        'already_have_account': 'Déjà un compte?',
        'create_account': 'Créer un Compte',
        'start_journey': "Commencez votre voyage d'épargne",
        'many_hands': 'Plusieurs mains allègent le travail',
        'together_stronger': 'Ensemble nous sommes plus forts',
        'groups': 'Groupes',
        'members': 'Membres',
        'total_saved': 'Total Épargné',
        'contribution': 'Contribution',
        'next_payout': 'Prochain Paiement',
        'view_group': 'Voir le Groupe',
        'admin': 'Admin',
        'member': 'Membre'
    },
    'pt': {
        'welcome': 'Bem-vindo',
        'login': 'Entrar',
        'signup': 'Cadastrar',
        'logout': 'Sair',
        'dashboard': 'Painel',
        'my_groups': 'Meus Grupos',
        'create_group': 'Criar Grupo',
        'join_group': 'Entrar no Grupo',
        'settings': 'Configurações',
        'profile': 'Perfil',
        'community_savings': 'Poupança Comunitária Simplificada',
        'username': 'Usuário',
        'password': 'Senha',
        'email': 'Email',
        'enter_username': 'Digite seu usuário',
        'enter_password': 'Digite sua senha',
        'enter_email': 'Digite seu email',
        'dont_have_account': 'Não tem conta?',
        'already_have_account': 'Já tem conta?',
        'create_account': 'Criar Conta',
        'start_journey': 'Comece sua jornada de poupança hoje',
        'many_hands': 'Muitas mãos aliviam o trabalho',
        'together_stronger': 'Juntos somos mais fortes',
        'groups': 'Grupos',
        'members': 'Membros',
        'total_saved': 'Total Poupado',
        'contribution': 'Contribuição',
        'next_payout': 'Próximo Pagamento',
        'view_group': 'Ver Grupo',
        'admin': 'Admin',
        'member': 'Membro'
    },
    'ar': {
        'welcome': 'مرحباً',
        'login': 'تسجيل الدخول',
        'signup': 'إنشاء حساب',
        'logout': 'تسجيل الخروج',
        'dashboard': 'لوحة التحكم',
        'my_groups': 'مجموعاتي',
        'create_group': 'إنشاء مجموعة',
        'join_group': 'انضم لمجموعة',
        'settings': 'الإعدادات',
        'profile': 'الملف الشخصي',
        'community_savings': 'التوفير الجماعي بسهولة',
        'username': 'اسم المستخدم',
        'password': 'كلمة المرور',
        'email': 'البريد الإلكتروني',
        'enter_username': 'أدخل اسم المستخدم',
        'enter_password': 'أدخل كلمة المرور',
        'enter_email': 'أدخل بريدك الإلكتروني',
        'dont_have_account': 'ليس لديك حساب؟',
        'already_have_account': 'لديك حساب بالفعل؟',
        'create_account': 'إنشاء حساب',
        'start_journey': 'ابدأ رحلة التوفير اليوم',
        'many_hands': 'الأيدي الكثيرة تخفف الحمل',
        'together_stronger': 'معاً نحن أقوى',
        'groups': 'المجموعات',
        'members': 'الأعضاء',
        'total_saved': 'إجمالي المدخرات',
        'contribution': 'المساهمة',
        'next_payout': 'الدفعة التالية',
        'view_group': 'عرض المجموعة',
        'admin': 'مشرف',
        'member': 'عضو'
    },
    'zh': {
        'welcome': '欢迎',
        'login': '登录',
        'signup': '注册',
        'logout': '退出',
        'dashboard': '仪表板',
        'my_groups': '我的群组',
        'create_group': '创建群组',
        'join_group': '加入群组',
        'settings': '设置',
        'profile': '个人资料',
        'community_savings': '简单的社区储蓄',
        'username': '用户名',
        'password': '密码',
        'email': '邮箱',
        'enter_username': '输入用户名',
        'enter_password': '输入密码',
        'enter_email': '输入邮箱',
        'dont_have_account': '没有账户？',
        'already_have_account': '已有账户？',
        'create_account': '创建账户',
        'start_journey': '今天开始您的储蓄之旅',
        'many_hands': '众人拾柴火焰高',
        'together_stronger': '团结就是力量',
        'groups': '群组',
        'members': '成员',
        'total_saved': '总储蓄',
        'contribution': '贡献',
        'next_payout': '下次支付',
        'view_group': '查看群组',
        'admin': '管理员',
        'member': '成员'
    },
    'hi': {
        'welcome': 'स्वागत है',
        'login': 'लॉग इन',
        'signup': 'साइन अप',
        'logout': 'लॉग आउट',
        'dashboard': 'डैशबोर्ड',
        'my_groups': 'मेरे समूह',
        'create_group': 'समूह बनाएं',
        'join_group': 'समूह में शामिल हों',
        'settings': 'सेटिंग्स',
        'profile': 'प्रोफाइल',
        'community_savings': 'सामुदायिक बचत आसान बनाई',
        'username': 'उपयोगकर्ता नाम',
        'password': 'पासवर्ड',
        'email': 'ईमेल',
        'enter_username': 'उपयोगकर्ता नाम दर्ज करें',
        'enter_password': 'पासवर्ड दर्ज करें',
        'enter_email': 'ईमेल दर्ज करें',
        'dont_have_account': 'खाता नहीं है?',
        'already_have_account': 'पहले से खाता है?',
        'create_account': 'खाता बनाएं',
        'start_journey': 'आज ही अपनी बचत यात्रा शुरू करें',
        'many_hands': 'कई हाथ मिलकर बोझ हल्का करते हैं',
        'together_stronger': 'साथ मिलकर हम मजबूत हैं',
        'groups': 'समूह',
        'members': 'सदस्य',
        'total_saved': 'कुल बचत',
        'contribution': 'योगदान',
        'next_payout': 'अगला भुगतान',
        'view_group': 'समूह देखें',
        'admin': 'व्यवस्थापक',
        'member': 'सदस्य'
    },
    'ja': {
        'welcome': 'ようこそ',
        'login': 'ログイン',
        'signup': '登録',
        'logout': 'ログアウト',
        'dashboard': 'ダッシュボード',
        'my_groups': 'マイグループ',
        'create_group': 'グループ作成',
        'join_group': 'グループに参加',
        'settings': '設定',
        'profile': 'プロフィール',
        'community_savings': 'コミュニティ貯蓄をシンプルに',
        'username': 'ユーザー名',
        'password': 'パスワード',
        'email': 'メール',
        'enter_username': 'ユーザー名を入力',
        'enter_password': 'パスワードを入力',
        'enter_email': 'メールを入力',
        'dont_have_account': 'アカウントをお持ちでない方',
        'already_have_account': 'アカウントをお持ちの方',
        'create_account': 'アカウント作成',
        'start_journey': '今日から貯蓄の旅を始めましょう',
        'many_hands': '多くの手が負担を軽くする',
        'together_stronger': '一緒なら強くなれる',
        'groups': 'グループ',
        'members': 'メンバー',
        'total_saved': '合計貯蓄',
        'contribution': '貢献',
        'next_payout': '次の支払い',
        'view_group': 'グループを見る',
        'admin': '管理者',
        'member': 'メンバー'
    },
    'ko': {
        'welcome': '환영합니다',
        'login': '로그인',
        'signup': '가입',
        'logout': '로그아웃',
        'dashboard': '대시보드',
        'my_groups': '내 그룹',
        'create_group': '그룹 만들기',
        'join_group': '그룹 가입',
        'settings': '설정',
        'profile': '프로필',
        'community_savings': '간편한 커뮤니티 저축',
        'username': '사용자 이름',
        'password': '비밀번호',
        'email': '이메일',
        'enter_username': '사용자 이름 입력',
        'enter_password': '비밀번호 입력',
        'enter_email': '이메일 입력',
        'dont_have_account': '계정이 없으신가요?',
        'already_have_account': '이미 계정이 있으신가요?',
        'create_account': '계정 만들기',
        'start_journey': '오늘 저축 여정을 시작하세요',
        'many_hands': '여러 손이 짐을 가볍게 한다',
        'together_stronger': '함께하면 더 강해집니다',
        'groups': '그룹',
        'members': '회원',
        'total_saved': '총 저축',
        'contribution': '기여',
        'next_payout': '다음 지급',
        'view_group': '그룹 보기',
        'admin': '관리자',
        'member': '회원'
    },
    'ru': {
        'welcome': 'Добро пожаловать',
        'login': 'Вход',
        'signup': 'Регистрация',
        'logout': 'Выход',
        'dashboard': 'Панель',
        'my_groups': 'Мои Группы',
        'create_group': 'Создать Группу',
        'join_group': 'Присоединиться',
        'settings': 'Настройки',
        'profile': 'Профиль',
        'community_savings': 'Простые Общественные Сбережения',
        'username': 'Имя пользователя',
        'password': 'Пароль',
        'email': 'Эл. почта',
        'enter_username': 'Введите имя пользователя',
        'enter_password': 'Введите пароль',
        'enter_email': 'Введите эл. почту',
        'dont_have_account': 'Нет аккаунта?',
        'already_have_account': 'Уже есть аккаунт?',
        'create_account': 'Создать Аккаунт',
        'start_journey': 'Начните путь накоплений сегодня',
        'many_hands': 'Много рук облегчают работу',
        'together_stronger': 'Вместе мы сильнее',
        'groups': 'Группы',
        'members': 'Участники',
        'total_saved': 'Всего Накоплено',
        'contribution': 'Взнос',
        'next_payout': 'Следующая Выплата',
        'view_group': 'Смотреть Группу',
        'admin': 'Админ',
        'member': 'Участник'
    },
    'de': {
        'welcome': 'Willkommen',
        'login': 'Anmelden',
        'signup': 'Registrieren',
        'logout': 'Abmelden',
        'dashboard': 'Dashboard',
        'my_groups': 'Meine Gruppen',
        'create_group': 'Gruppe Erstellen',
        'join_group': 'Gruppe Beitreten',
        'settings': 'Einstellungen',
        'profile': 'Profil',
        'community_savings': 'Gemeinschaftliches Sparen Einfach Gemacht',
        'username': 'Benutzername',
        'password': 'Passwort',
        'email': 'E-Mail',
        'enter_username': 'Benutzername eingeben',
        'enter_password': 'Passwort eingeben',
        'enter_email': 'E-Mail eingeben',
        'dont_have_account': 'Kein Konto?',
        'already_have_account': 'Bereits ein Konto?',
        'create_account': 'Konto Erstellen',
        'start_journey': 'Starte heute deine Sparreise',
        'many_hands': 'Viele Hände machen die Arbeit leicht',
        'together_stronger': 'Zusammen sind wir stärker',
        'groups': 'Gruppen',
        'members': 'Mitglieder',
        'total_saved': 'Gesamt Gespart',
        'contribution': 'Beitrag',
        'next_payout': 'Nächste Auszahlung',
        'view_group': 'Gruppe Ansehen',
        'admin': 'Admin',
        'member': 'Mitglied'
    }
}


def get_ui_text(key: str, language: str = 'en') -> str:
    """Get UI text in the specified language."""
    if language not in UI_TRANSLATIONS:
        language = 'en'
    
    translations = UI_TRANSLATIONS.get(language, UI_TRANSLATIONS['en'])
    return translations.get(key, UI_TRANSLATIONS['en'].get(key, key))


def get_all_ui_texts(language: str = 'en') -> dict:
    """Get all UI translations for a language."""
    if language not in UI_TRANSLATIONS:
        language = 'en'
    return UI_TRANSLATIONS.get(language, UI_TRANSLATIONS['en'])


def get_language_options() -> list:
    """Get list of available languages with flags."""
    return [
        {'code': code, 'name': name, 'flag': LANGUAGE_FLAGS.get(code, '🌐')}
        for code, name in SUPPORTED_LANGUAGES.items()
    ]
