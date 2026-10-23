/*
CHECKBHYT - READ-ONLY XML schema discovery
Run in SSMS with the database context set to the HIS database.
This script only reads metadata and sample rows; it does not execute stored procedures,
write data, or create/recreate XML.

1) Set the XML database name below if it differs.
*/
SET NOCOUNT ON;

DECLARE @XmlDatabase sysname = N'eHospital_ThienHanh_XML';

-- A. Exact columns and SQL types for XML1_CV130 ... XML15_CV130.
DECLARE @sql nvarchar(max) = N'
SELECT
    s.name AS schema_name,
    t.name AS table_name,
    c.column_id,
    c.name AS column_name,
    ty.name AS data_type,
    c.max_length,
    c.precision,
    c.scale,
    c.is_nullable
FROM ' + QUOTENAME(@XmlDatabase) + N'.sys.tables AS t
JOIN ' + QUOTENAME(@XmlDatabase) + N'.sys.schemas AS s ON s.schema_id = t.schema_id
JOIN ' + QUOTENAME(@XmlDatabase) + N'.sys.columns AS c ON c.object_id = t.object_id
JOIN ' + QUOTENAME(@XmlDatabase) + N'.sys.types AS ty ON ty.user_type_id = c.user_type_id
WHERE t.name LIKE N''XML%[_]CV130''
ORDER BY s.name, t.name, c.column_id;';
EXEC sys.sp_executesql @sql;

-- B. Identify likely relationship columns in the HIS database and XML database.
-- This is metadata-only. It does not assume a specific mapping.
SELECT
    DB_NAME() AS database_name,
    s.name AS schema_name,
    t.name AS table_name,
    c.name AS column_name,
    ty.name AS data_type
FROM sys.tables AS t
JOIN sys.schemas AS s ON s.schema_id = t.schema_id
JOIN sys.columns AS c ON c.object_id = t.object_id
JOIN sys.types AS ty ON ty.user_type_id = c.user_type_id
WHERE c.name IN (
    N'MA_LK', N'MaLK', N'MaLienKet', N'SoPhieu_BA', N'SoTiepNhan',
    N'BenhAn_Id', N'TiepNhan_Id', N'XacNhanChiPhi_Id'
)
ORDER BY s.name, t.name, c.name;

-- C. List candidate tables with MA_LK / patient IDs / confirmation ID across XML database.
DECLARE @sql2 nvarchar(max) = N'
SELECT
    s.name AS schema_name,
    t.name AS table_name,
    c.name AS column_name,
    ty.name AS data_type
FROM ' + QUOTENAME(@XmlDatabase) + N'.sys.tables AS t
JOIN ' + QUOTENAME(@XmlDatabase) + N'.sys.schemas AS s ON s.schema_id = t.schema_id
JOIN ' + QUOTENAME(@XmlDatabase) + N'.sys.columns AS c ON c.object_id = t.object_id
JOIN ' + QUOTENAME(@XmlDatabase) + N'.sys.types AS ty ON ty.user_type_id = c.user_type_id
WHERE c.name IN (
    N''MA_LK'', N''MaLK'', N''MaLienKet'', N''SoPhieu_BA'', N''SoTiepNhan'',
    N''BenhAn_Id'', N''TiepNhan_Id'', N''XacNhanChiPhi_Id'', N''CHI_TIEU'', N''GIA_TRI'', N''STT''
)
ORDER BY s.name, t.name, c.name;';
EXEC sys.sp_executesql @sql2;

-- D. Optional: small, read-only sample from XML tables after reviewing the discovered names.
-- Uncomment only the specific table and schema found in section A:
-- SELECT TOP (20) * FROM [dbo].[XML1_CV130];
