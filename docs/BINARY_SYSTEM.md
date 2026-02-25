# System Budowania i Weryfikacji Binariów

Ten dokument opisuje architekturę i logikę systemu CI/CD odpowiedzialnego za tworzenie oraz testowanie binariów aplikacji OpenData Tool (zarówno PyInstaller jak i pyApp).

## 1. Architektura Systemu

System składa się z trzech głównych komponentów:
1.  **Build Wheel**: Tworzy uniwersalny pakiet `.whl`, który jest podstawą dla wszystkich binariów.
2.  **Build Binary**: Joby budujące (oddzielne dla PyInstaller i pyApp), które osadzają kod aplikacji w pliku wykonywalnym.
3.  **Verify Binary**: Reużywalny workflow sprawdzający, czy binaria działają na docelowych systemach operacyjnych.

## 2. System pyApp (Embedded Python)

pyApp jest preferowanym formatem dla Linux i macOS ze względu na mniejszy rozmiar i lepszą izolację.

### Konfiguracja Budowania (`pyapp-build-binary.yml`)
Kluczowe zmienne środowiskowe:
*   `PYAPP_PROJECT_PATH`: Ścieżka do pliku `.whl`. Na Windows musi być skonwertowana przez `cygpath -w`.
*   `PYAPP_DISTRIBUTION_EMBED="true"`: Wymusza osadzenie interpretera Pythona wewnątrz binarki.
*   `PYAPP_DISTRIBUTION_VARIANT_CPU="v1"`: **Krytyczne dla Linux x86_64**. Wymusza generyczną architekturę procesora, co zapewnia działanie na starszych maszynach (brak wymogu AVX2).
*   `PYAPP_PIP_EXTRA_ARGS="--only-binary :all:"`: Zapobiega próbom kompilacji zależności ze źródeł, co często zawodzi w izolowanych środowiskach binarnych.

## 3. System Weryfikacji (`reusable-verify-binary.yml`)

Weryfikacja została zaprojektowana tak, aby odróżnić błędy samej binarki od problemów z wydajnością runnerów CI.

### Dwuetapowy Test (Two-Stage Verification)

#### Krok 1: Smoke Test (`--version`)
Binarka jest uruchamiana z flagą `--version`. 
*   **Cel**: Sprawdzenie czy interpreter Pythona startuje, czy architektura CPU jest poprawna i czy wszystkie moduły są zainstalowane.
*   **Logika**: Pierwsze uruchomienie pyApp wyzwala wewnętrzny `pip install`. Test ma ustawiony długi timeout (90s), aby pozwolić na tę operację.
*   **Diagnoza**: Jeśli ten krok zawiedzie z błędem `Illegal instruction`, oznacza to problem z architekturą CPU. Jeśli `ModuleNotFoundError` - błąd konfiguracji buildu.

#### Krok 2: Functional Test (API)
Aplikacja jest uruchamiana w trybie headless (`--headless --no-browser --api`).
*   **Cel**: Sprawdzenie czy serwer HTTP wstaje i poprawnie odpowiada na zapytania API.
*   **Logika**: Skrypt wykonuje do 15 prób połączenia z endpointem `/api/projects` przy użyciu `curl`.

## 4. Rozwiązane Problemy (Knowledge Base)

### Windows `ModuleNotFoundError`
*   **Przyczyna**: Git Bash na Windows zwraca ścieżki w stylu Unix (`/d/a/...`), których Rustowy `PathBuf` nie rozpoznaje jako plików. W efekcie wheel nie był osadzany.
*   **Rozwiązanie**: Użycie `cygpath -w` przed przekazaniem ścieżki do PyApp.

### Debian 13 / Starsze Linuxy ("Illegal Instruction")
*   **Przyczyna**: PyApp domyślnie używa wariantu `v3` (AVX2). Starsze procesory lub niektóre wirtualizacje nie wspierają tych instrukcji.
*   **Rozwiązanie**: Wymuszenie `PYAPP_DISTRIBUTION_VARIANT_CPU="v1"`.

### macOS Flakiness
*   **Przyczyna**: Brak komendy `timeout` na macOS powodował błędy skryptów testowych (Exit 127).
*   **Rozwiązanie**: Zastąpienie `timeout` pętlą `while kill -0` w bashu.

## 5. Utrzymanie i Debugowanie

W przypadku problemów w przyszłości:
1.  **Logi Smoke Testu**: Zawsze sprawdzaj wyjście z `--version`. To najszybszy sposób na znalezienie błędów importu.
2.  **Verbose Pip**: Jeśli moduły nadal nie są znajdowane, dodaj `export PYAPP_PIP_VERBOSE="1"` do workflow budowania. Logi instalacji pojawią się podczas pierwszego uruchomienia binarki w fazie weryfikacji.
3.  **Architektura**: Jeśli binarka działa na jednej maszynie a na innej nie, sprawdź flagi CPU (`cat /proc/cpuinfo | grep avx2`). Jeśli brak AVX2, upewnij się że build używa `v1`.
