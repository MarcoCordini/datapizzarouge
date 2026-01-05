"""
Modulo per pulizia HTML e conversione a testo pulito e semantico.
Usa BeautifulSoup per parsing e rimozione di elementi indesiderati.
"""
import re
import logging
from typing import Dict, Optional
from bs4 import BeautifulSoup, Comment

logger = logging.getLogger(__name__)


class HTMLCleaner:
    """
    Pulisce HTML e lo converte in testo strutturato per RAG.
    """

    # Tag da rimuovere completamente
    UNWANTED_TAGS = [
        "script",
        "style",
        "noscript",
        "iframe",
        "object",
        "embed",
        "applet",
        "canvas",
        "svg",
        "link",
        "meta",
    ]

    # Tag di navigazione/boilerplate da rimuovere
    BOILERPLATE_TAGS = [
        "nav",
        "header",
        "footer",
        "aside",
        "form",
    ]

    # Selettori CSS per elementi comuni di boilerplate
    BOILERPLATE_SELECTORS = [
        "nav",
        ".nav",
        ".navigation",
        ".navbar",
        ".menu",
        "header",
        ".header",
        "footer",
        ".footer",
        "aside",
        ".sidebar",
        ".advertisement",
        ".ads",
        ".ad",
        ".cookie-banner",
        ".cookie-notice",
        ".social-share",
        ".related-posts",
        ".comments",
    ]

    def __init__(self, preserve_structure: bool = True):
        """
        Inizializza HTMLCleaner.

        Args:
            preserve_structure: Se True, preserva la struttura con headings
        """
        self.preserve_structure = preserve_structure

    def clean(self, html: str, url: Optional[str] = None) -> Dict[str, any]:
        """
        Pulisce HTML e restituisce testo strutturato.

        Args:
            html: HTML grezzo da pulire
            url: URL della pagina (opzionale, per logging)

        Returns:
            Dict con:
                - text: Testo pulito
                - title: Titolo della pagina
                - headings: Lista di headings (h1, h2, etc.)
                - word_count: Numero di parole
        """
        try:
            soup = BeautifulSoup(html, "lxml")

            # Estrai titolo prima di pulire
            title_tag = soup.find("title")
            title = title_tag.get_text().strip() if title_tag else ""

            # Rimuovi commenti HTML
            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                comment.extract()

            # Rimuovi tag indesiderati
            for tag_name in self.UNWANTED_TAGS:
                for tag in soup.find_all(tag_name):
                    tag.decompose()

            # Rimuovi boilerplate usando selettori CSS
            for selector in self.BOILERPLATE_SELECTORS:
                for element in soup.select(selector):
                    element.decompose()

            # Cerca main content (article, main, content div)
            main_content = self._extract_main_content(soup)

            if main_content:
                soup = main_content
                logger.debug(f"Estratto main content per {url}")

            # Estrai headings prima della conversione a testo
            headings = self._extract_headings(soup)

            # Converti a testo preservando struttura
            if self.preserve_structure:
                text = self._extract_structured_text(soup)
            else:
                text = soup.get_text(separator="\n", strip=True)

            # Pulisci whitespace
            text = self._clean_whitespace(text)

            # Conta parole
            word_count = len(text.split())

            result = {
                "text": text,
                "title": title,
                "headings": headings,
                "word_count": word_count,
            }

            logger.debug(f"Pulito HTML: {word_count} parole, {len(headings)} headings")

            return result

        except Exception as e:
            logger.error(f"Errore pulendo HTML per {url}: {e}")
            return {
                "text": "",
                "title": "",
                "headings": [],
                "word_count": 0,
            }

    def _extract_main_content(self, soup: BeautifulSoup) -> Optional[BeautifulSoup]:
        """
        Cerca di estrarre il contenuto principale della pagina.

        Args:
            soup: BeautifulSoup object

        Returns:
            BeautifulSoup object del contenuto principale, o None
        """
        # Prova tag semantici HTML5
        main_content = soup.find("main")
        if main_content:
            return main_content

        # Prova article tag
        article = soup.find("article")
        if article:
            return article

        # Prova div comuni per content
        content_selectors = [
            "div[id*='content']",
            "div[class*='content']",
            "div[id*='main']",
            "div[class*='main']",
            "div[class*='post']",
            "div[class*='article']",
            "div[id*='article']",
        ]

        for selector in content_selectors:
            content = soup.select_one(selector)
            if content:
                return content

        # Se non trovi niente, ritorna None (useremo tutto il body)
        return None

    def _extract_headings(self, soup: BeautifulSoup) -> list:
        """
        Estrae tutti i headings (h1-h6) dalla pagina.

        Args:
            soup: BeautifulSoup object

        Returns:
            Lista di dict con {level, text} per ogni heading
        """
        headings = []

        for level in range(1, 7):
            for heading in soup.find_all(f"h{level}"):
                text = heading.get_text().strip()
                if text:
                    headings.append({"level": level, "text": text})

        return headings

    def _extract_structured_text(self, soup: BeautifulSoup) -> str:
        """
        Estrae testo preservando struttura con headings e paragrafi.

        Args:
            soup: BeautifulSoup object

        Returns:
            Testo strutturato
        """
        lines = []

        # Processa elementi in ordine
        for element in soup.descendants:
            if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                text = element.get_text().strip()
                if text:
                    # Aggiungi newline prima dei headings per separazione
                    lines.append("\n")
                    # Aggiungi heading con marker di livello
                    level_marker = "#" * int(element.name[1])
                    lines.append(f"{level_marker} {text}")
                    lines.append("")

            elif element.name == "p":
                text = element.get_text().strip()
                if text:
                    lines.append(text)
                    lines.append("")

            elif element.name in ["li"]:
                text = element.get_text().strip()
                if text:
                    lines.append(f"• {text}")

            elif element.name == "br":
                lines.append("")

        return "\n".join(lines)

    def _clean_whitespace(self, text: str) -> str:
        """
        Pulisce whitespace eccessivo dal testo.

        Args:
            text: Testo da pulire

        Returns:
            Testo pulito
        """
        # Rimuovi spazi multipli
        text = re.sub(r" +", " ", text)

        # Rimuovi tab
        text = re.sub(r"\t+", " ", text)

        # Normalizza newlines (max 2 consecutive)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Rimuovi spazi a inizio/fine riga
        lines = [line.strip() for line in text.split("\n")]

        # Rimuovi righe vuote consecutive
        cleaned_lines = []
        prev_empty = False
        for line in lines:
            if line:
                cleaned_lines.append(line)
                prev_empty = False
            elif not prev_empty:
                cleaned_lines.append(line)
                prev_empty = True

        return "\n".join(cleaned_lines).strip()


def clean_html(html: str, url: Optional[str] = None) -> Dict[str, any]:
    """
    Funzione helper per pulire HTML.

    Args:
        html: HTML da pulire
        url: URL opzionale per logging

    Returns:
        Dict con testo pulito e metadata
    """
    cleaner = HTMLCleaner()
    return cleaner.clean(html, url)


if __name__ == "__main__":
    # Test HTMLCleaner
    test_html = """
    <html>
    <head><title>Test Page</title></head>
    <body>
        <nav>Skip this navigation</nav>
        <header>Header content</header>
        <main>
            <h1>Main Title</h1>
            <p>This is the main content.</p>
            <h2>Subtitle</h2>
            <p>More content here.</p>
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
            </ul>
        </main>
        <footer>Footer content</footer>
        <script>console.log('remove me');</script>
    </body>
    </html>
    """

    result = clean_html(test_html)
    print("=== Test HTML Cleaner ===")
    print(f"Title: {result['title']}")
    print(f"Headings: {result['headings']}")
    print(f"Word count: {result['word_count']}")
    print(f"\nText:\n{result['text']}")
