# Instrukcja Instalacji OpenData Tool dla Testerów

Witaj w programie testów OpenData Tool! Ta instrukcja przeprowadzi Cię przez proces uruchomienia narzędzia na Twoim komputerze. Narzędzie zostało przygotowane tak, aby **nie wymagało instalacji Pythona** ani żadnych skomplikowanych bibliotek. Wszystko, czego potrzebujesz, znajduje się w jednym pliku.

Uwaga: Wszystkie pliki binarne podążają za wzorem nazwy: `opendata-<platforma>-pyapp-<wersja>`.

---

## 🪟 Windows (10 / 11)

1. **Pobierz:** Ściągnij plik `opendata-win-pyapp-<wersja>.exe` z portalu testowego.
2. **Uruchom:** Kliknij dwukrotnie na pobrany plik.
3. **Ostrzeżenie SmartScreen:** Ponieważ program jest w fazie wczesnych testów i nie posiada jeszcze certyfikatu cyfrowego, Windows może wyświetlić niebieskie okno "Windows protected your PC" (System Windows ochronił ten komputer).
   - Kliknij napis **"More info"** (Więcej informacji).
   - Kliknij przycisk **"Run anyway"** (Uruchom mimo to).
4. **Pierwsze uruchomienie:** Przy pierwszym włączeniu program może potrzebować od 30 do 60 sekund na przygotowanie środowiska pracy. Prosimy o cierpliwość – kolejne uruchomienia będą błyskawiczne.
5. **Jak sprawdzić czy działa?** Na pasku zadań (koło zegara) pojawi się mała ikona OpenData Tool. Kliknij ją prawym przyciskiem myszy i wybierz **"Open Dashboard"**, aby otworzyć interfejs w przeglądarce.

---

## 🍎 macOS (Intel oraz M1/M2/M3)

1. **Pobierz właściwą wersję:**
   - Jeśli masz procesor Apple Silicon (M1, M2, M3): wybierz `opendata-macos-arm-pyapp-<wersja>`.
   - Jeśli masz starszy procesor Intel: wybierz `opendata-macos-intel-pyapp-<wersja>`.
2. **Uruchomienie (Omijanie zabezpieczeń):** Apple rygorystycznie podchodzi do aplikacji spoza App Store. Przy próbie otwarcia zobaczysz komunikat, że aplikacja pochodzi od "nieznanego dewelopera".
   - **Metoda 1:** Kliknij na plik **prawym przyciskiem myszy** i wybierz **Otwórz** (Open). Wtedy w oknie dialogowym pojawi się przycisk "Otwórz", którego nie ma przy zwykłym kliknięciu.
   - **Metoda 2:** Wejdź w *Ustawienia Systemowe -> Prywatność i bezpieczeństwo*. Zjedź na dół i kliknij przycisk **"Open Anyway"** (Otwórz mimo to) przy nazwie programu.
3. **Uprawnienia:** Program może poprosić o dostęp do plików w folderze "Pobrane" lub innych lokalizacjach, które wskażesz do analizy. Zaakceptuj te prośby.

---

## 🐧 Linux (Ubuntu, Debian, Fedora, itp.)

1. **Pobierz:** Ściągnij plik `opendata-linux-pyapp-<wersja>`.
2. **Nadaj uprawnienia:** Po pobraniu plik musi stać się "wykonywalny".
   - **Graficznie:** Kliknij prawym na plik -> *Właściwości* -> *Uprawnienia* -> Zaznacz **"Zezwól na wykonywanie pliku jako programu"**.
   - **Terminalowo:** `chmod +x opendata-linux-pyapp-*`
3. **Uruchom:** Kliknij dwukrotnie lub wpisz w terminalu `./opendata-linux-pyapp-*`.
4. **Zależności:** Program jest niemal w pełni samowystarczalny, ale na bardzo "odchudzonych" wersjach Linuxa może brakować biblioteki `libfuse2` lub standardowych bibliotek C. Jeśli program się nie uruchamia, sprawdź logi w terminalu.

---

## 💡 Co warto wiedzieć (Potencjalne problemy)

### ⏳ Pierwszy start to "Cicha Instalacja"
Technologia **PyApp**, której używamy, przy pierwszym uruchomieniu wykonuje automatyczną konfigurację Twojego środowiska pracy (tworzy tzw. wirtualne środowisko). 
- **Bądź cierpliwy:** Podczas pierwszego uruchomienia okno programu (lub ikona w zasobniku) może pojawić się z dużym opóźnieniem (nawet do minuty). System w tym czasie wypakowuje setki plików potrzebnych do działania narzędzi AI.
- **Dysk twardy:** Program zajmuje około 300-500 MB po wypakowaniu w Twoim folderze domowym (katalog `.cache/pyapp` lub podobny).
- **Internet:** Mimo że większość plików jest w pakiecie, przy pierwszym starcie zalecamy połączenie z internetem, aby program mógł zweryfikować poprawność instalacji.

### 🌐 Interfejs w przeglądarce
OpenData Tool działa jako serwer w tle. Interfejs użytkownika otwiera się w Twojej domyślnej przeglądarce pod adresem `http://localhost:8080`. 
- Jeśli okno przeglądarki się nie otworzy automatycznie, spróbuj wpisać ten adres ręcznie.
- Program nie wysyła Twoich danych badawczych na serwer bez Twojej zgody (AI potrzebuje wysłać tylko fragmenty tekstu do analizy po Twoim zalogowaniu).

### 🛠️ Gdzie szukać pomocy?
Jeśli program się zawiesi lub nie chce się uruchomić:
1. Sprawdź, czy ikona w zasobniku systemowym (koło zegara) jest aktywna.
2. Spróbuj zamknąć program (Exit w menu ikony) i uruchomić go ponownie.
3. Jeśli błąd się powtarza, wyślij nam informację na adres `jochym@ifj.edu.pl`, dołączając (jeśli to możliwe) zrzut ekranu z ewentualnym błędem.

---
*Dziękujemy za pomoc w testowaniu OpenData Tool! Twoje uwagi są dla nas bezcenne.*
