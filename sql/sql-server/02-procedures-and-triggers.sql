DROP PROCEDURE IF EXISTS bonus_dla_osoby;
DROP PROCEDURE IF EXISTS ZmienCeneWynajmuWZakresieDat;
GO
DROP TRIGGER IF EXISTS zmiana_kosztu_utrymania;
DROP TRIGGER IF EXISTS Przypisz_Umowe_Innemu_Agentowi;
GO

/*Procedura zwiększa cenę wynajmu o procent podany w parametrze dla aktywnych umów, które zostały zawarte w okresie między dwiema określonymi datami, sprawdzając, czy data zakończenia umowy jest późniejsza niż dzisiejsza. Dodatkowo, cena wynajmu jest zwiększana o zadany procent tylko wtedy, gdy dom związany z umową ma koszt utrzymania niższy niż wartość podana w parametrze*/

CREATE PROCEDURE ZmienCeneWynajmuWZakresieDat
    @data_od DATE, 
    @data_do DATE, 
    @procent_wzrostu INT, 
    @koszt_utrzymania INT
AS
BEGIN
    DECLARE @v_id_umowy INT;
    DECLARE @v_cena_wynajmu DECIMAL(10, 2);
    DECLARE @v_data_zakonczenia DATE;
    DECLARE @v_id_domu INT;
    DECLARE @v_koszt_utrzymania DECIMAL(10, 2);
    DECLARE @nowa_cena DECIMAL(10, 2);
    DECLARE cursor_umowy CURSOR FOR 
        SELECT u.ID_Umowy, u.Cena_wynajmu, u.Data_zakonczenia, u.Dom_Id_domu
        FROM Umowa_o_wynajem u
        JOIN Dom d ON u.Dom_Id_domu = d.ID_domu
        WHERE u.Data_rozpoczecia BETWEEN @data_od AND @data_do;
    OPEN cursor_umowy;
    FETCH NEXT FROM cursor_umowy INTO @v_id_umowy, @v_cena_wynajmu, @v_data_zakonczenia, @v_id_domu;
    WHILE @@FETCH_STATUS = 0
    BEGIN
        IF @v_data_zakonczenia > GETDATE()
        BEGIN
            SELECT @v_koszt_utrzymania = Koszt_Utrzymania
            FROM Dom
            WHERE ID_domu = @v_id_domu;
            IF @v_koszt_utrzymania < @koszt_utrzymania
            BEGIN
                SET @nowa_cena = @v_cena_wynajmu + (@v_cena_wynajmu * @procent_wzrostu / 100);
                UPDATE Umowa_o_wynajem
                SET Cena_wynajmu = @nowa_cena
                WHERE ID_Umowy = @v_id_umowy;
                PRINT CONCAT('Umowa o ID: ', @v_id_umowy, ' ma teraz nową cenę: ', @nowa_cena);
            END
        END
        FETCH NEXT FROM cursor_umowy INTO @v_id_umowy, @v_cena_wynajmu, @v_data_zakonczenia, @v_id_domu;
    END
    CLOSE cursor_umowy;
    DEALLOCATE cursor_umowy;
END;



/*Procedura przyznaje bonus osobie na podstawie jej roli (właściciela lub najemcy) przez zwiększenie ceny rynkowej domów o 2% dla właścicieli i 
zmniejszenie ceny wynajmu o 10% dla najemców, identyfikujac osobę po imieniu i nazwisku (załóżmy że imienia i nazwiska są niepowtarzalne).*/
GO
CREATE PROCEDURE bonus_dla_osoby
    @imie VARCHAR(20),
    @nazwisko VARCHAR(20)
AS
BEGIN
    DECLARE @v_pesel BIGINT;
    DECLARE @v_is_wlasciciel BIGINT;
    DECLARE @v_is_najemca BIGINT;
    SELECT @v_pesel = Pesel
    FROM Osoba
    WHERE Imie = @imie AND Nazwisko = @nazwisko;
    SELECT @v_is_wlasciciel = COUNT(*)
    FROM Wlasciciel
    WHERE Osoba_Pesel = @v_pesel;
    SELECT @v_is_najemca = COUNT(*)
    FROM Najemca
    WHERE Osoba_Pesel = @v_pesel;
    IF @v_is_wlasciciel > 0
    BEGIN
        UPDATE d
        SET d.Cena_rynkowa = d.Cena_rynkowa * 1.02
        FROM Dom d
        JOIN Przestrzen p ON d.Nieruchomosc_ID = p.ID_Przestrzen
        WHERE p.Wlasciciel_Osoba_Pesel = @v_pesel;
        PRINT CONCAT('Właściciel ', @imie, ' ', @nazwisko, ' otrzymał bonus. Cena rynkowa domów została zwiększona o 2%.');
    END
    IF @v_is_najemca > 0
    BEGIN
        UPDATE u
        SET u.Cena_wynajmu = u.Cena_wynajmu * 0.9
        FROM Umowa_o_wynajem u
        WHERE u.Najemca_Pesel = @v_pesel;
        PRINT CONCAT('Najemca ', @imie, ' ', @nazwisko, ' otrzymał bonus. Cena wynajmu została zmniejszona o 10%.');
    END
END;




/*wyzwalacz monitoruje zmiany w tabeli Dom dotyczące kosztu utrzymania nieruchomości. Po zaktualizowaniu tego kosztu, jeśli nowy koszt przekroczy ustalony próg 1000, wyzwalacz automatycznie zwiększa cenę wynajmu dla wszystkich powiązanych umów o 5%*/

GO
CREATE TRIGGER zmiana_kosztu_utrymania
ON Dom
AFTER UPDATE
AS
BEGIN
 DECLARE @NewMaintenanceCost INT;
 DECLARE @OldMaintenanceCost INT;
 DECLARE @RentalPrice INT;
 DECLARE @AgreementID INT;
 SELECT @OldMaintenanceCost = deleted.Koszt_Utrzymania, 
 @NewMaintenanceCost = inserted.Koszt_Utrzymania
 FROM inserted
 INNER JOIN deleted ON inserted.ID_domu = deleted.ID_domu;
 IF @NewMaintenanceCost > 1000 AND @NewMaintenanceCost != @OldMaintenanceCost
 BEGIN
     DECLARE rental_cursor CURSOR FOR
         SELECT u.ID_Umowy, u.Cena_wynajmu
         FROM Umowa_o_wynajem u
         INNER JOIN Dom d ON u.Dom_Id_domu = d.ID_domu
         WHERE d.ID_domu = (SELECT ID_domu FROM inserted);
     OPEN rental_cursor;
     FETCH NEXT FROM rental_cursor INTO @AgreementID, @RentalPrice;
     WHILE @@FETCH_STATUS = 0
     BEGIN
      UPDATE Umowa_o_wynajem
      SET Cena_wynajmu = @RentalPrice + (@RentalPrice * 0.05) 
      WHERE ID_Umowy = @AgreementID;
      PRINT CONCAT('Zwiększono o 5% cene wynajmu dla umow która ma ID: ',@AgreementID  );
      FETCH NEXT FROM rental_cursor INTO @AgreementID, @RentalPrice;
     END;
     CLOSE rental_cursor;
     DEALLOCATE rental_cursor;
    END;
END;




/*Wyzwalacz przypisuje domy usuniętej umowy wynajmu do pierwszego agenta z tej samej firmy, który ma aktywne umowy. Działa to tylko w przypadku, gdy agent związany z usuniętą umową nie ma już innych aktywnych umów, zapewniając, że domy nie zostaną pozostawione bez przypisanego agenta, ale tylko wtedy, gdy do umowy przypisany jest agent.*/

GO
CREATE TRIGGER Przypisz_Umowe_Innemu_Agentowi
ON Umowa_o_wynajem
AFTER DELETE, UPDATE
AS
BEGIN
    DECLARE @AgentPesel BIGINT;
    DECLARE @NowyAgentPesel BIGINT;
    DECLARE @FirmName NVARCHAR(20);
    DECLARE @Today DATE = GETDATE();
    DECLARE @UmowaId INT;
    IF UPDATE(Agent_nieruchomosci_Pesel) OR EXISTS (SELECT 1 FROM deleted)
    BEGIN
        DECLARE deleted_cursor CURSOR FOR 
            SELECT DISTINCT Agent_nieruchomosci_Pesel
           FROM deleted;
        OPEN deleted_cursor;
        FETCH NEXT FROM deleted_cursor INTO @AgentPesel;
        WHILE @@FETCH_STATUS = 0
        BEGIN
            IF NOT EXISTS (SELECT 1
            FROM Umowa_o_wynajem
            WHERE Agent_nieruchomosci_Pesel = @AgentPesel
            AND Data_zakonczenia > @Today)
            BEGIN
                SELECT @FirmName = Nazwa_firmy
                FROM Agent_nieruchomosci
                WHERE Osoba_Pesel = @AgentPesel;
                
                SELECT TOP 1 @NowyAgentPesel = a.Osoba_Pesel
                FROM Agent_nieruchomosci a
                WHERE a.Nazwa_firmy = @FirmName
                AND a.Osoba_Pesel != @AgentPesel
                AND (SELECT COUNT(*)
                FROM Umowa_o_wynajem u
                WHERE u.Agent_nieruchomosci_Pesel = a.Osoba_Pesel
                AND u.Data_zakonczenia > @Today) > 1;
                IF @NowyAgentPesel IS NOT NULL
                BEGIN
                 SELECT TOP 1 @UmowaId = ID_Umowy
                 FROM Umowa_o_wynajem
                 WHERE Agent_nieruchomosci_Pesel = @NowyAgentPesel
                 AND Data_zakonczenia > @Today;
                 UPDATE Umowa_o_wynajem
                 SET Agent_nieruchomosci_Pesel = @AgentPesel
                 WHERE ID_Umowy = @UmowaId;
                 PRINT CONCAT('Umowa o ID ', @UmowaId, ' została przypisana do agenta o PESEL: ', @AgentPesel);
                END
                ELSE
                BEGIN
                 PRINT CONCAT('Agent o PESEL ', @AgentPesel, ' nie ma już żadnych aktywnych umów i brak jest dostępnych kolegów w tej samej firmie.');
                END;
            END;
            FETCH NEXT FROM deleted_cursor INTO @AgentPesel;
        END;
        CLOSE deleted_cursor;
        DEALLOCATE deleted_cursor;
    END;
END;
GO


