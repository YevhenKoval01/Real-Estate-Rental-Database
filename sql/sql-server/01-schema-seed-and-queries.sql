-- Reset the demo schema in dependency order so the script can be rerun.
DROP TABLE IF EXISTS Umowa_o_wynajem;
DROP TABLE IF EXISTS Dom;
DROP TABLE IF EXISTS Przestrzen;
DROP TABLE IF EXISTS Agent_nieruchomosci;
DROP TABLE IF EXISTS Najemca;
DROP TABLE IF EXISTS Wlasciciel;
DROP TABLE IF EXISTS Osoba;
GO

-- Created by Vertabelo (http://vertabelo.com)
-- Last modification date: 2024-12-30 16:22:38.043

-- tables
-- Table: Agent_nieruchomosci
CREATE TABLE Agent_nieruchomosci (
    Osoba_Pesel BIGINT NOT NULL,
    Nazwa_firmy varchar(20) NOT NULL,
    CONSTRAINT Agent_nieruchomosci_pk PRIMARY KEY (Osoba_Pesel)
);

-- Table: Dom
CREATE TABLE Dom (
    ID_domu BIGINT NOT NULL,
    Nieruchomosc_ID BIGINT NOT NULL,
    Powierzchnia_Calkowita int NOT NULL,
    Ilosc_Pieter int NOT NULL,
    Obecnosc_garazu char(1) NOT NULL,
    Koszt_Utrzymania int NOT NULL,
    Cena_rynkowa int NOT NULL,
    CONSTRAINT Dom_pk PRIMARY KEY (ID_domu)
);

-- Table: Najemca
CREATE TABLE Najemca (
    Osoba_Pesel BIGINT NOT NULL,
    Przyczyna_najmu varchar(30) NOT NULL,
    CONSTRAINT Najemca_pk PRIMARY KEY (Osoba_Pesel)
);

-- Table: Osoba
CREATE TABLE Osoba (
    Pesel BIGINT NOT NULL,
    Imie varchar(20) NOT NULL,
    Nazwisko varchar(20) NOT NULL,
    CONSTRAINT Osoba_pk PRIMARY KEY (Pesel)
);

-- Table: Przestrzen
CREATE TABLE Przestrzen (
    ID_Przestrzen BIGINT NOT NULL,
    Powierzchnia int NOT NULL,
    Lokalizacja varchar(20) NOT NULL, 
    Wlasciciel_Osoba_Pesel BIGINT NOT NULL,
    CONSTRAINT Przestrzen_pk PRIMARY KEY (ID_Przestrzen)
);

-- Table: Umowa_o_wynajem
CREATE TABLE Umowa_o_wynajem (
    ID_Umowy BIGINT NOT NULL,
    Cena_wynajmu int NOT NULL,
    Data_rozpoczecia date NOT NULL,
    Data_zakonczenia date NOT NULL,
    Najemca_Pesel BIGINT NOT NULL,
    Agent_nieruchomosci_Pesel BIGINT NULL,
    Dom_Id_domu BIGINT NOT NULL,
    CONSTRAINT Umowa_o_wynajem_pk PRIMARY KEY (ID_Umowy)
);

-- Table: Wlasciciel
CREATE TABLE Wlasciciel (
    Osoba_Pesel BIGINT NOT NULL,
    staz int NOT NULL,
    CONSTRAINT Wlasciciel_pk PRIMARY KEY (Osoba_Pesel)
);

-- Foreign keys
-- Reference: Agent_nieruchomosci_Osoba (table: Agent_nieruchomosci)
ALTER TABLE Agent_nieruchomosci ADD CONSTRAINT Agent_nieruchomosci_Osoba
    FOREIGN KEY (Osoba_Pesel)
    REFERENCES Osoba (Pesel);

-- Reference: Dom_Przestrzen (table: Dom)
ALTER TABLE Dom ADD CONSTRAINT Dom_Przestrzen
    FOREIGN KEY (Nieruchomosc_ID)
    REFERENCES Przestrzen (ID_Przestrzen);

-- Reference: Najemca_Osoba (table: Najemca)
ALTER TABLE Najemca ADD CONSTRAINT Najemca_Osoba
    FOREIGN KEY (Osoba_Pesel)
    REFERENCES Osoba (Pesel);

-- Reference: Przestrzen_Wlasciciel (table: Przestrzen)
ALTER TABLE Przestrzen ADD CONSTRAINT Przestrzen_Wlasciciel
    FOREIGN KEY (Wlasciciel_Osoba_Pesel)
    REFERENCES Wlasciciel (Osoba_Pesel);

-- Reference: Umowa_o_wynajem_Agent_nieruchomosci (table: Umowa_o_wynajem)
ALTER TABLE Umowa_o_wynajem ADD CONSTRAINT Umowa_o_wynajem_Agent_nieruchomosci
    FOREIGN KEY (Agent_nieruchomosci_Pesel)
    REFERENCES Agent_nieruchomosci (Osoba_Pesel);

-- Reference: Umowa_o_wynajem_Dom (table: Umowa_o_wynajem)
ALTER TABLE Umowa_o_wynajem ADD CONSTRAINT Umowa_o_wynajem_Dom
    FOREIGN KEY (Dom_Id_domu)
    REFERENCES Dom (ID_domu);

-- Reference: Umowa_o_wynajem_Najemca (table: Umowa_o_wynajem)
ALTER TABLE Umowa_o_wynajem ADD CONSTRAINT Umowa_o_wynajem_Najemca
    FOREIGN KEY (Najemca_Pesel)
    REFERENCES Najemca (Osoba_Pesel);

-- Reference: Wlasciciel_Osoba (table: Wlasciciel)
ALTER TABLE Wlasciciel ADD CONSTRAINT Wlasciciel_Osoba
    FOREIGN KEY (Osoba_Pesel)
    REFERENCES Osoba (Pesel);

-- End of file.


-- Wstawianie osób (właściciele, najemcy, agenci)
INSERT INTO Osoba (Pesel, Imie, Nazwisko) VALUES (12345678901, 'Jan', 'Kowalski');
INSERT INTO Osoba (Pesel, Imie, Nazwisko) VALUES (23456789012, 'Anna', 'Nowak');
INSERT INTO Osoba (Pesel, Imie, Nazwisko) VALUES (34567890123, 'Piotr', 'Wiśniewski');
INSERT INTO Osoba (Pesel, Imie, Nazwisko) VALUES (45678901234, 'Kasia', 'Zielińska');
INSERT INTO Osoba (Pesel, Imie, Nazwisko) VALUES (56789012345, 'Marek', 'Więckowski');
INSERT INTO Osoba (Pesel, Imie, Nazwisko) VALUES (67890123456, 'Adam', 'Nowak'); 
INSERT INTO Osoba (Pesel, Imie, Nazwisko) VALUES (78901234567, 'Ewa', 'Kowalska');
INSERT INTO Osoba (Pesel, Imie, Nazwisko) VALUES (89012345678, 'Tomasz', 'Lewandowski');
INSERT INTO Osoba (Pesel, Imie, Nazwisko) VALUES (90123456789, 'Barbara', 'Wiśniewska');

-- Wstawianie właścicieli
INSERT INTO Wlasciciel (Osoba_Pesel, Staz) VALUES (12345678901, 10);
INSERT INTO Wlasciciel (Osoba_Pesel, Staz) VALUES (23456789012, 5);
INSERT INTO Wlasciciel (Osoba_Pesel, Staz) VALUES (67890123456, 8);
INSERT INTO Wlasciciel (Osoba_Pesel, Staz) VALUES (78901234567, 12);

-- Wstawianie najemców
INSERT INTO Najemca (Osoba_Pesel, Przyczyna_najmu) VALUES (34567890123, 'Praca');
INSERT INTO Najemca (Osoba_Pesel, Przyczyna_najmu) VALUES (45678901234, 'Studia');
INSERT INTO Najemca (Osoba_Pesel, Przyczyna_najmu) VALUES (89012345678, 'Rodzina');
INSERT INTO Najemca (Osoba_Pesel, Przyczyna_najmu) VALUES (90123456789, 'Biznes');

-- Wstawianie agentów nieruchomości
INSERT INTO Agent_nieruchomosci (Osoba_Pesel, Nazwa_firmy) VALUES (56789012345, 'Best Estates');

-- Wstawianie przestrzeni
INSERT INTO Przestrzen (ID_Przestrzen, Powierzchnia, Lokalizacja, Wlasciciel_Osoba_Pesel)
VALUES (1, 1000, 'Warszawa', 12345678901);
INSERT INTO Przestrzen (ID_Przestrzen, Powierzchnia, Lokalizacja, Wlasciciel_Osoba_Pesel)
VALUES (2, 750, 'Kraków', 12345678901);
INSERT INTO Przestrzen (ID_Przestrzen, Powierzchnia, Lokalizacja, Wlasciciel_Osoba_Pesel)
VALUES (3, 500, 'Poznań', 23456789012);
INSERT INTO Przestrzen (ID_Przestrzen, Powierzchnia, Lokalizacja, Wlasciciel_Osoba_Pesel)
VALUES (4, 800, 'Gdańsk', 67890123456);
INSERT INTO Przestrzen (ID_Przestrzen, Powierzchnia, Lokalizacja, Wlasciciel_Osoba_Pesel)
VALUES (5, 600, 'Łódź', 78901234567);

-- Wstawianie domów
INSERT INTO Dom (ID_Domu, Nieruchomosc_ID, Powierzchnia_Calkowita, Ilosc_Pieter, Obecnosc_garazu, Koszt_Utrzymania, Cena_rynkowa)
VALUES (1, 1, 200, 2, 'Y', 500, 1000000);
INSERT INTO Dom (ID_Domu, Nieruchomosc_ID, Powierzchnia_Calkowita, Ilosc_Pieter, Obecnosc_garazu, Koszt_Utrzymania, Cena_rynkowa)
VALUES (2, 2, 150, 1, 'N', 300, 750000);
INSERT INTO Dom (ID_Domu, Nieruchomosc_ID, Powierzchnia_Calkowita, Ilosc_Pieter, Obecnosc_garazu, Koszt_Utrzymania, Cena_rynkowa)
VALUES (3, 4, 300, 3, 'Y', 400, 1200000);
INSERT INTO Dom (ID_Domu, Nieruchomosc_ID, Powierzchnia_Calkowita, Ilosc_Pieter, Obecnosc_garazu, Koszt_Utrzymania, Cena_rynkowa)
VALUES (4, 5, 250, 2, 'N', 350, 800000);

-- Wstawianie umów wynajmu
INSERT INTO Umowa_o_wynajem (ID_Umowy, Cena_Wynajmu, Data_rozpoczecia, Data_zakonczenia, Najemca_Pesel, Agent_nieruchomosci_Pesel, Dom_ID_Domu)
VALUES (1, 2500, CONVERT(DATE, '2024-01-01', 120), CONVERT(DATE, '2024-12-31', 120), 34567890123, NULL, 1);
INSERT INTO Umowa_o_wynajem (ID_Umowy, Cena_Wynajmu, Data_rozpoczecia, Data_zakonczenia, Najemca_Pesel, Agent_nieruchomosci_Pesel, Dom_ID_Domu)
VALUES (2, 2000, CONVERT(DATE, '2023-06-01', 120), CONVERT(DATE, '2023-12-31', 120), 45678901234, 56789012345, 2);
INSERT INTO Umowa_o_wynajem (ID_Umowy, Cena_Wynajmu, Data_rozpoczecia, Data_zakonczenia, Najemca_Pesel, Agent_nieruchomosci_Pesel, Dom_ID_Domu)
VALUES (3, 3000, CONVERT(DATE, '2024-02-01', 120), CONVERT(DATE, '2024-12-31', 120), 89012345678, 56789012345, 3);
INSERT INTO Umowa_o_wynajem (ID_Umowy, Cena_Wynajmu, Data_rozpoczecia, Data_zakonczenia, Najemca_Pesel, Agent_nieruchomosci_Pesel, Dom_ID_Domu)
VALUES (4, 2800, CONVERT(DATE, '2023-03-01', 120), CONVERT(DATE, '2024-03-31', 120), 90123456789, 56789012345, 4);
GO


--1 Znajdź wszystkich właścicieli, którzy mają przynajmniej jedną nieruchomość o powierzchni większej niż 100 m², i wyświetl ich imiona, nazwiska oraz staż.
SELECT Osoba.Imie, Osoba.Nazwisko, Wlasciciel.Staz
FROM Osoba
JOIN Wlasciciel ON Osoba.Pesel = Wlasciciel.Osoba_Pesel
JOIN Przestrzen ON Wlasciciel.Osoba_Pesel = Przestrzen.Wlasciciel_Osoba_Pesel
WHERE Przestrzen.Powierzchnia > 100;

--2 Wyświetl wszystkie nieruchomości, które mają właścicieli o stażu większym niż 10 lat.
SELECT Przestrzen.ID_Przestrzen, Przestrzen.Lokalizacja
FROM Przestrzen
JOIN Wlasciciel ON Przestrzen.Wlasciciel_Osoba_Pesel = Wlasciciel.Osoba_Pesel
WHERE Wlasciciel.Staz > 10;

--3 Wyświetl nazwiska właścicieli, którzy mają dokładnie jedną nieruchomość.
SELECT Osoba.Nazwisko
FROM Osoba
JOIN Wlasciciel ON Osoba.Pesel = Wlasciciel.Osoba_Pesel
JOIN Przestrzen ON Wlasciciel.Osoba_Pesel = Przestrzen.Wlasciciel_Osoba_Pesel
GROUP BY Osoba.Nazwisko
HAVING COUNT(Przestrzen.ID_Przestrzen) = 1;

--4 Znajdź agentów, którzy obsługują więcej niż 5 umów najmu.
SELECT Agent_nieruchomosci.Nazwa_firmy
FROM Agent_nieruchomosci
JOIN Umowa_o_wynajem ON Agent_nieruchomosci.Osoba_Pesel = Umowa_o_wynajem.Agent_nieruchomosci_Pesel
GROUP BY Agent_nieruchomosci.Nazwa_firmy
HAVING COUNT(Umowa_o_wynajem.ID_Umowy) > 5;

--5 Znajdź najemców, którzy mają więcej umów najmu niż najemca z numerem PESEL kończącym się na "56789", oraz średnia cena wynajmu ich umów przekracza 2000. Wyświetl ich imię i nazwisko.
SELECT o.Imie, o.Nazwisko
FROM Najemca n
JOIN Osoba o ON n.Osoba_Pesel = o.Pesel
JOIN Umowa_o_wynajem u ON n.Osoba_Pesel = u.Najemca_Pesel
GROUP BY o.Pesel, o.Imie, o.Nazwisko
HAVING COUNT(u.ID_Umowy) > (
    SELECT COUNT(u2.ID_Umowy)
    FROM Umowa_o_wynajem u2
    JOIN Najemca n2 ON u2.Najemca_Pesel = n2.Osoba_Pesel
    JOIN Osoba o2 ON n2.Osoba_Pesel = o2.Pesel
    WHERE o2.Pesel LIKE '%56789')
AND AVG(u.Cena_Wynajmu) > 2000;

--6 Znajdź wszystkie nieruchomości, które mają umowy wynajmu o cenie wynajmu wyższej niż średnia cena wynajmu ze wszystkich umów w systemie
SELECT p.*
FROM Przestrzen p
JOIN Dom d ON p.ID_Przestrzen = d.Nieruchomosc_ID
JOIN Umowa_o_wynajem u ON d.ID_Domu = u.Dom_ID_Domu
WHERE u.Cena_Wynajmu > (
    SELECT AVG(Cena_Wynajmu)
    FROM Umowa_o_wynajem);

--7 Znajdź wszystkie umowy o wynajem, w których cena wynajmu jest wyższa niż średnia cena wynajmu dla nieruchomości zlokalizowanych w Warszawie.
SELECT u.*
FROM Umowa_o_wynajem u
JOIN Dom d ON u.Dom_ID_Domu = d.ID_Domu
JOIN Przestrzen p ON d.Nieruchomosc_ID = p.ID_Przestrzen
WHERE u.Cena_Wynajmu > (
    SELECT AVG(u2.Cena_Wynajmu)
    FROM Umowa_o_wynajem u2
    JOIN Dom d2 ON u2.Dom_ID_Domu = d2.ID_Domu
    JOIN Przestrzen p2 ON d2.Nieruchomosc_ID = p2.ID_Przestrzen
    WHERE p2.Lokalizacja = 'Warszawa');

--8 Znajdź imiona i nazwiska najemców, którzy nie są jednocześnie właścicielami nieruchomości.
SELECT o.Imie, o.Nazwisko
FROM Najemca n
JOIN Osoba o ON n.Osoba_Pesel = o.Pesel
WHERE n.Osoba_Pesel NOT IN (
    SELECT wlasciciele.Osoba_Pesel
    FROM (SELECT w.Osoba_Pesel
    FROM Wlasciciel w) wlasciciele);

--9 Znajdź imiona i nazwiska wszystkich właścicieli posiadających co najmniej jedną nieruchomość o powierzchni większej niż średnia powierzchnia wszystkich nieruchomości.
SELECT o.Imie, o.Nazwisko
FROM Wlasciciel w
JOIN Osoba o ON w.Osoba_Pesel = o.Pesel
JOIN Przestrzen p ON w.Osoba_Pesel = p.Wlasciciel_Osoba_Pesel
GROUP BY o.Imie, o.Nazwisko
HAVING MAX(p.Powierzchnia) > (
    SELECT AVG(Powierzchnia)
    FROM Przestrzen);

--10 Pokaż imiona i nazwiska najemców, których średnia cena wynajmu jest wyższa niż średnia cena wynajmu dla wszystkich najemców.
SELECT o.Imie, o.Nazwisko
FROM Najemca n
JOIN Osoba o ON n.Osoba_Pesel = o.Pesel
JOIN Umowa_o_wynajem u ON n.Osoba_Pesel = u.Najemca_Pesel
GROUP BY o.Imie, o.Nazwisko
HAVING AVG(u.Cena_Wynajmu) > (
    SELECT AVG(Cena_Wynajmu)
    FROM Umowa_o_wynajem);

--11 Znajdź wszystkie umowy wynajmu, gdzie cena wynajmu jest równa najwyższej cenie wynajmu dla tego samego właściciela.
SELECT u.*
FROM Umowa_o_wynajem u
JOIN Dom d ON u.Dom_ID_Domu = d.ID_Domu
JOIN Przestrzen p ON d.Nieruchomosc_ID = p.ID_Przestrzen
WHERE u.Cena_Wynajmu = (
    SELECT MAX(u2.Cena_Wynajmu)
    FROM Umowa_o_wynajem u2
    JOIN Dom d2 ON u2.Dom_ID_Domu = d2.ID_Domu
    JOIN Przestrzen p2 ON d2.Nieruchomosc_ID = p2.ID_Przestrzen
    WHERE p2.Wlasciciel_Osoba_Pesel = p.Wlasciciel_Osoba_Pesel);

--12 Znajdź wszystkie domy, których cena rynkowa jest wyższa niż najwyższa cena rynkowa domu należącego do właściciela o nazwisku "Nowak".
SELECT d.*
FROM Dom d
JOIN Przestrzen p ON d.Nieruchomosc_ID = p.ID_Przestrzen
WHERE d.Cena_rynkowa > (
    SELECT MAX(d2.Cena_rynkowa)
    FROM Dom d2
    JOIN Przestrzen p2 ON d2.Nieruchomosc_ID = p2.ID_Przestrzen
    JOIN Wlasciciel w ON p2.Wlasciciel_Osoba_Pesel = w.Osoba_Pesel
    JOIN Osoba o ON w.Osoba_Pesel = o.Pesel
    WHERE o.Nazwisko = 'Nowak');

--13 Znajdź imiona i nazwiska najemców, którzy mają więcej umów o wynajem niż średnia liczba umów podpisanych przez właścicieli nieruchomości o powierzchni większej niż 300 metrów kwadratowych.
SELECT o.Imie, o.Nazwisko
FROM Najemca n
JOIN Osoba o ON n.Osoba_Pesel = o.Pesel
JOIN Umowa_o_wynajem u ON n.Osoba_Pesel = u.Najemca_Pesel
GROUP BY o.Imie, o.Nazwisko
HAVING COUNT(u.ID_Umowy) > (
    SELECT AVG(liczba_umow)
    FROM (
        SELECT COUNT(u2.ID_Umowy) AS liczba_umow
        FROM Umowa_o_wynajem u2
        JOIN Dom d ON u2.Dom_ID_Domu = d.ID_Domu
        JOIN Przestrzen p ON d.Nieruchomosc_ID = p.ID_Przestrzen
        JOIN Wlasciciel w ON p.Wlasciciel_Osoba_Pesel = w.Osoba_Pesel
        WHERE p.Powierzchnia > 300
        GROUP BY w.Osoba_Pesel
    ) AS subquery );
