# Rozszerzony Plan Rozwoju Interfejsu AI (Roadmapa)

Niniejszy dokument szczegółowo opisuje kolejne kroki rozwoju modułu AI w projekcie OpenData Tool, ze szczególnym uwzględnieniem wsparcia dla wielu dostawców i zaawansowanych funkcji pomocniczych.

## Faza 1 i 2: Fundamenty [ZREALIZOWANE]
- Wprowadzenie wzorca Fasady (`AIService`) i dostawców (`GoogleProvider`, `OpenAIProvider`).
- Obsługa konfiguracji wielu silników w `UserSettings`.
- Integracja z UI (zakładki w wizardzie konfiguracji).

## Faza 3: Search Grounding dla Dostawców Zewnętrznych
Obecnie tylko Google Gemini posiada natywne ugruntowanie w wynikach wyszukiwania. Dla OpenAI/Ollama należy zaimplementować mechanizm RAG (Retrieval-Augmented Generation):

### Kroki implementacji:
1.  **Integracja Search API:** Dodanie obsługi zewnętrznego dostawcy wyników (np. [Serper.dev](https://serper.dev/) lub Google Custom Search JSON API).
2.  **Mechanizm Reasoning Loop:**
    - Agent (OpenAI/Llama) otrzymuje instrukcję: "Jeśli potrzebujesz danych, których nie masz (np. aktualny DOI), zwróć zapytanie w formacie `SEARCH: <query>`".
    - `AIService` przechwytuje to zapytanie, wykonuje wyszukiwanie i wstrzykuje wyniki (snippety) z powrotem do kontekstu.
3.  **Optymalizacja Kosztów/Tokenów:** Agregacja wyników wyszukiwania do najistotniejszych 3-5 fragmentów, aby nie przekroczyć okna kontekstowego mniejszych modeli lokalnych.

## Faza 4: Streaming i Responsywność UI
Modele lokalne (szczególnie na słabszym sprzęcie) generują tekst powoli.

### Kroki implementacji:
1.  **Async Generators:** Zmiana metody `ask_agent` na asynchroniczny generator (`async def ask_agent(...) -> AsyncGenerator[str, None]`).
2.  **Reaktywność w NiceGUI:**
    - Wykorzystanie `ui.markdown().bind_content()` lub bezpośrednia aktualizacja elementu w pętli zdarzeń.
    - Dodanie wskaźnika "Tokens per second" dla modeli lokalnych.

## Faza 5: Diagnostyka i Local-LLM UX
Użytkownicy modeli lokalnych często napotykają problemy z łącznością.

### Kroki implementacji:
1.  **Health Checks:** Przycisk "Test Connection" w wizardzie, wykonujący szybki call do `/models` lub `/tags`.
2.  **Discovery API:** Dla Ollama – automatyczne pobieranie listy modeli pobranych na dysk użytkownika i wypełnianie nimi dropdowna w UI.
3.  **Fallback Logic:** Jeśli model lokalny nie odpowiada (np. serwer Ollama wyłączony), UI powinno zaproponować szybki powrót do Gemini z jasnym komunikatem błędu.

## Faza 6: Unifikacja Narzędzi (Function Calling)
Google i OpenAI mają różne formaty definicji narzędzi.

### Kroki implementacji:
1.  **OpenData Tool Schema:** Zdefiniowanie wspólnego interfejsu dla narzędzi (np. `fetch_arxiv`, `verify_orcid`).
2.  **Translator Narzędzi:** Moduł konwertujący ten schemat na `tools` (Google) lub `functions` (OpenAI/Ollama).
3.  **Client-Side Tools:** Przeniesienie logiki narzędzi (np. parsowanie BibTeX) do warstwy agenta, aby każdy silnik mógł z nich korzystać w ten sam sposób.

## Faza 7: Testy End-to-End i Benchmarking
- **Mock Provider:** Stworzenie providera testowego, który zwraca deterministyczne odpowiedzi JSON do testów E2E bez zużywania limitów API.
- **Vibe-Check Suite:** Zestaw testowy w `pytest`, który sprawdza czy dany model (np. Llama3 vs GPT-4) poprawnie ekstrahuje metadane z tych samych fixture'ów.

---
*Dokument ten stanowi wytyczne dla przyszłych prac deweloperskich.*
