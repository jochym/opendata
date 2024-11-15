# Przykładowe zapisy z Regulaminu RODBUK:

Osobą uprawnioną do założenia Konta Deponującego w Repozytorium jest **pracownik naukowy, doktorant lub student** afiliowany przez Współadministratora.

**Deponujący ponosi pełną odpowiedzialność** za zamieszczone Dane Badawcze oraz za ewentualne naruszenie praw autorskich i majątkowych osób trzecich oraz praw pokrewnych. W przypadku poniesienia przez Współadministratora jakichkolwiek kosztów wynikających z działań Deponującego, Deponujący zobowiązuje się pokryć wskazane koszty w całości (w tym z tytułu odszkodowania lub zadośćuczynienia, koszty postępowania sądowego oraz egzekucyjnego).

**W przypadku projektów wieloautorskich lub międzyuczelnianych** osobą odpowiedzialną za zdeponowanie Danych Badawczych w Repozytorium jest kierownik projektu lub wyznaczona przez niego osoba. Kierownik projektu jest zobowiązany **posiadać zgody pozostałych współautorów** na deponowanie Danych Badawczych w Repozytorium **w formie pisemnych oświadczeń**. Osoba odpowiedzialna za zdeponowanie danych jest zobowiązana przedłożyć ww. oświadczenia lub ich odpisy niezwłocznie, na każde żądanie Kuratora Danych.

Deponujący przyjmuje do wiadomości, że zdeponowane przez niego **dane mogą być przeglądane przez Kuratora Danych oraz Administratora Repozytorium** w ramach okresowego monitorowania zgodności ze stanem faktycznym złożonych oświadczeń, dotyczących danych osobowych i autorskich praw majątkowych.

Metadane zdeponowanego Zbioru Danych podlegają **weryfikacji przez Data Stewarda** w zakresie kompletności i poprawności a następnie publikowane są w Repozytorium.

Każdemu zdeponowanemu Zbiorowi Danych zostaje nadany **Identyfikator DOI**. Jeden Zbiór Danych może mieć nadany wyłącznie jeden indywidualny Identyfikator DOI. W celu nadania indywidualnego Identyfikatora DOI **korzysta się z usług DOI RA, c**o wiąże się z przekazaniem Metadanych do DOI RA.

W przypadku projektów międzyuczelnianych regulaminem obowiązującym jest regulamin zatwierdzony w instytucji naukowej kierownika projektu.

Dane Badawcze są przechowywane w Repozytorium **przez okres obowiązywania Umowy Głównej.**

# Instrukcja zakładania konta w RODBUK

<https://userguide.bg.agh.edu.pl/8-2/zakladanie-konta-logowanie/akademia-gorniczo-hutnicza/>

1. Przed pierwszym deponowaniem danych w RODBUK należy założyć konto używając adresu poczty w domenie swojej uczelni.
2. W sekcji „Zdeponuj dane w repozytorium swojej uczelni" należy wybrać właściwą uczelnię. Nastąpi przekierowanie do strony **uczelnianego serwera uwierzytelniani**a, gdzie trzeba się zalogować.
3. Po zalogowaniu nastąpi przekierowanie z powrotem do witryny RODBUK -- podczas pierwszego logowania należy sprawdzić poprawność wprowadzonych danych, zaakceptować [regulamin](https://agh.rodbuk.pl/pl/terms-of-use) i kliknąć **„Utwórz konto"**.
4. Po weryfikacji i nadaniu uprawnień przez Data Stewarda można rozpocząć deponowanie danych w RODBUK. Weryfikacja konta powinna zająć około 1 dzień roboczy.

# Instrukcja deponowania metadanych

<https://userguide.bg.agh.edu.pl/8-2/deponowanie-metadanych/>

1. Po weryfikacji konta przez Data Stewarda można już dodawać zbiory danych.
2. Po wybraniu kolekcji w sekcji„ Dodaj dane -- Nowy zbiór danych" należy wypełnić w formularzu pola metadanych (obowiązkowe są oznaczone gwiazdką). Niektóre z nich są powtarzalne.
3. W przypadku pól: *schemat identyfikowania, dziedzina nauki wg Ministerstwa Edukacji i Nauki ([MNiSW.pdf](https://docs.cyfronet.pl/download/attachments/130288104/MEiN.pdf?version=5&modificationDate=1673260705000&api=v2)), dziedzina nauki wg Organisation for Economic Co-operation and Development ([OECD.pdf](https://docs.cyfronet.pl/download/attachments/130288104/OECD.pdf?version=1&modificationDate=1673002878000&api=v2)), powiązane publikacje, powiązany zbiór danych, finansowanie, rodzaj danych w zbiorze* należy wybrać odpowiednie **wartości z rozwijalnej listy.**
4. Po zapisaniu powstanie **wersja robocza zbioru danych**, która będzie miała **już przypisany numer DOI, nieaktywny do momentu zweryfikowania i opublikowania** zbioru przez Data Stewarda. Zbiór danych będzie miał status „Wersja robocza".
5. Wprowadzone metadane są dostępne bez ograniczeń, zgodnie z regulaminem RODBUK i powszechnie obowiązującym prawem.
6. W RODBUK  jest stosowany otwarty standard opisu metadanych [[Dublin Core]{.underline}](https://www.dublincore.org/)

# Instrukcja deponowania danych badawczych

<https://userguide.bg.agh.edu.pl/>

1. W sekcji „Pliki" za pomocą przycisku „Wybierz pliki do dodania" należy załączyć wybrane do udostępnienia pliki tworzące zbiór danych (wraz z plikiem[ readme.txt](https://libraries.ou.edu/content/how-make-readmetxt-file)).
2. Do RODBUK można przesłać pojedynczy plik o maksymalnej wielkości **4 GB**. Przesyłanie większych plików wymaga użycia **tokena API**, który można wygenerować pod kontem użytkownika wybierając Token API a następnie utwórz Token (jest on ważny przez rok), oraz skryptu dostępnego na [GitHub](https://github.com/gdcc/python-dvuploader). Przed zdeponowaniem dużych plików prosimy o kontakt z administratorem RODBUK.
3. W przypadku stosowania programów do kompresji i archiwizacji danych zalecamy **ZIP lub 7-Zip**, które mają otwartą architekturę i są powszechnie dostępne.
4. Zgodnie z wytycznymi instytucji finansujących badania naukowe, dane badawcze należy zapisywać w [formatach otwartych](https://pl.wikipedia.org/wiki/Format_otwarty) (np. **OpenDocument, PNG, FLAC, WebM, HTML, CSS),** powszechnie dostępnych i bezpłatnych z wyjątkiem sytuacji, kiedy konwersja plików z oprogramowania specjalistycznego do otwartego może wpłynąć na jakość danych.
5. W ramach jednego zbioru danych można stosować różne rodzaje dostępu do poszczególnych plików. Dostęp do pliku może być objęty **embargiem** czasowym określonym w momencie deponowania danych lub **Ograniczony/Restricted** permanentnie z możliwością uzyskania dostępu do niego od autora zbioru danych (poprzez kontakt mailowy). Dostęp do pliku objętego embargiem zostaje automatycznie odblokowany wraz z jego upływem. Maksymalny okres embarga stosowany w RODBUK to **36 miesięcy**.

   Są 3 rodzaje dostępu:
   * **Publiczny/Public** -- możliwy dla wszystkich użytkowników RODBUK-a.\
   * **Ograniczony/Restricted** -- limitowany z możliwością uzyskania dostępu do konkretnego pliku/ów poprzez kontakt mailowy z jego Deponującym.\
   * **Objęty embargiem/Embargoed** -- możliwy (automatycznie) po upływie określonego czasu przez Deponującego zbiór danych (max. okres embarga stosowany w RODBUK wynosi 36 miesięcy).
6. O ograniczeniu dostępu do poszczególnych plików **decyduje Deponujący**. Po jego stronie są również dodatkowe działania mające na celu weryfikację osoby, która poprosiła o udostępnienie danych.
7. **Data Steward weryfikuje** wprowadzony opis zbioru pod kątem jego **kompletności i poprawności.** Na ten proces składa się sprawdzenie poprawności metadanych oraz załączonych plików. Jeżeli opis i pliki zostały wprowadzone poprawnie -- zbiór danych zostanie opublikowany a w razie wątpliwości, **Data Steward może odesłać Deponującemu zbiór do poprawy,** kontaktując się z nim mailowo. Po opublikowaniu zbioru indywidualny **numer DOI** (ang. Digital Object Identifier) **będzie aktywny i nie ma już możliwości wprowadzenia zmian**. Istnieje możliwość utworzenia kolejnych, numerowanych wersji zbioru danych na bazie istniejącej, już opublikowanej wersji.
8. Opublikowany **zbiór danych nie podlega usunięciu z RODBUK.** W szczególnych przypadkach, takich jak naruszenie praw autorskich i innych praw własności intelektualnej, podejrzenie o popełnienie plagiatu, istnieje możliwość jego wycofania. W tym celu należy zwrócić się do Data Stewarda danej instytucji. Wycofanie zbioru danych obejmuje usunięcie wszystkich składających się na niego wersji. Publicznie dostępne pozostają podstawowe informacje dotyczące usuniętego zbioru (tzw. tombstone), czyli cytowanie i powód usunięcia danych. Pełny opis metadanych pozostaje widoczny jedynie dla osób, które posiadają role systemowe umożliwiające wycofanie zbioru.

[[Przykładowy plik README]{.underline}](https://userguide.bg.agh.edu.pl/wp-content/uploads/2024/01/readme_template-2.txt)

[[Preferowane formaty plików w RODBUK]{.underline}](https://userguide.bg.agh.edu.pl/wp-content/uploads/2024/01/Preferowane-formaty-plikow-pl.pdf)

!\[\]\[4]

\![https://userguide.bg.agh.edu.pl/wp-content/uploads/2024/07/pl1.png]

# Wybór licencji

<https://userguide.bg.agh.edu.pl/8-2/wybor-licencji/>

Licencje CC, dla baz danych do programów komputerowych.

Jeżeli zaproponowane licencje nie spełniają wymagań Deponującego, jest możliwość wyboru tzw. **licencji niestandardowej**, w której należy określić warunki, na jakich zbiór danych będzie udostępniony.

# Zabezpieczenie i długoterminowa archiwizacja

RODBUK zapewnia długoterminowe archiwizowanie danych na serwerach ACK Cyfronet AGH. Kopie plików z danymi są automatycznie tworzone w czasie rzeczywistym, a kopie metadanych raz na dobę. Kopie bezpieczeństwa są przechowywane w różnych lokalizacjach.

**Uwierzytelnianie**

W ramach zachowania bezpieczeństwa każdy nowy użytkownik przy zakładaniu indywidualnego konta w RODBUK jest weryfikowany przez Centralny System Uwierzytelniania Danych właściwej uczelni. Procedurę realizuje się za pomocą protokołów [OIDC] (OpenID Connect) lub [SAML2]. Każdorazowe logowanie wymaga loginu (adres e-mail) i hasła uwierzytelniającego (nadane przy pierwszym logowaniu).

**Dożywotność danych**

Dane zdeponowane w RODBUK nie podlegają wycofaniu przez autorów. W szczególnych przypadkach (np. naruszenie przepisów prawa autorskiego osób trzecich + plagiat) dane zostaną przeniesione do archiwum zamkniętego.

**Długoterminowa archiwizacja**

Wszystkie dokumenty zgromadzone w RODBUK są przechowywane i udostępniane bezterminowo, z zachowaniem zasad bezpieczeństwa danych. W przypadku wycofania się z inicjatywy RODBUK jednej z uczelni może ona p**rzenieść zgromadzone dane na jej instancji do innego repozytorium**. W razie zaistnienia sytuacji zamknięcia RODBUK **współzałożyciele podejmą starania zmierzające do przeniesienia danych do innego repozytorium, z zachowaniem ciągłości poprawnego funkcjonowania nadanych numerów DOI.** Osoby, które zdeponowały swoje dane badawcze w RODBUK, o tym fakcie zostaną poinformowane oficjalnym komunikatem.

**Dostępność w czasie**

Cyfronet AGH zobowiązuje się zapewnić gwarantowany czas dostępności do RODBUK na poziomie 99%.

# FAQ

<https://userguide.bg.agh.edu.pl/8-2/faq/>

## 

[4]: media/image1.png {width="5.145833333333333in" height="4.3597222222222225in"}
[https://userguide.bg.agh.edu.pl/wp-content/uploads/2024/07/pl1.png]: media/image2.png {width="4.927083333333333in" height="4.849975940507437in"}
[OIDC]: https://openid.net/connect/
[SAML2]: https://en.wikipedia.org/wiki/SAML_2.0