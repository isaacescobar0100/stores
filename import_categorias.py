import sqlite3

conn = sqlite3.connect('data/restaurantes.db')
cursor = conn.cursor()

# Verificar si existe la columna padre_id
cursor.execute("PRAGMA table_info(categorias_maestras)")
columns = [col[1] for col in cursor.fetchall()]
if 'padre_id' not in columns:
    cursor.execute('ALTER TABLE categorias_maestras ADD COLUMN padre_id INTEGER')

# Limpiar existentes
cursor.execute('DELETE FROM categorias_maestras')

# Insertar todas las categorías de producción
categorias = [
    (1, None, 'Hamburguesas', '/static/uploads/categorias/cat_797c253e.png', 1, 1),
    (2, None, 'Pizza', 'https://cdn-icons-png.flaticon.com/128/3595/3595458.png', 2, 1),
    (3, None, 'Hot Dogs', '/static/uploads/categorias/cat_1d84a8a5.png', 3, 1),
    (4, None, 'Papas Fritas', '/static/uploads/categorias/cat_6e0da2ad.png', 4, 1),
    (5, None, 'Sandwiches', '/static/uploads/categorias/cat_2cdb1a3d.png', 5, 1),
    (6, None, 'Tacos', '/static/uploads/categorias/cat_e9e8d872.png', 6, 1),
    (7, None, 'Burritos', '/static/uploads/categorias/cat_ea875cb2.png', 7, 1),
    (8, None, 'Nachos', '/static/uploads/categorias/cat_25e288a7.png', 8, 1),
    (9, None, 'Quesadillas', '/static/uploads/categorias/cat_27fdc95a.png', 9, 1),
    (10, None, 'Empanadas', '/static/uploads/categorias/cat_1b76f217.png', 17, 1),
    (11, None, 'Alitas', '/static/uploads/categorias/cat_5c32a9e2.png', 4, 1),
    (12, None, 'Nuggets', '/static/uploads/categorias/cat_9ab44995.png', 12, 1),
    (13, None, 'Sushi', '/static/uploads/categorias/cat_5ac9b5cd.png', 13, 1),
    (14, None, 'Ramen', '/static/uploads/categorias/cat_06a99d5b.png', 14, 1),
    (15, None, 'Poke Bowl', 'https://cdn-icons-png.flaticon.com/128/2276/2276878.png', 15, 0),
    (16, None, 'Wok', 'https://cdn-icons-png.flaticon.com/128/1046/1046786.png', 16, 0),
    (17, None, 'Arroz Chino', 'https://cdn-icons-png.flaticon.com/128/3480/3480458.png', 17, 0),
    (18, None, 'Pasta', 'https://cdn-icons-png.flaticon.com/128/3480/3480507.png', 18, 0),
    (19, None, 'Lasaña', 'https://cdn-icons-png.flaticon.com/128/5141/5141224.png', 19, 0),
    (20, None, 'Paella', 'https://cdn-icons-png.flaticon.com/128/3480/3480599.png', 20, 0),
    (21, None, 'Curry', 'https://cdn-icons-png.flaticon.com/128/2276/2276962.png', 21, 0),
    (22, None, 'Pollo', 'https://cdn-icons-png.flaticon.com/128/1046/1046751.png', 22, 0),
    (23, None, 'Carnes', 'https://cdn-icons-png.flaticon.com/128/3143/3143643.png', 23, 0),
    (24, None, 'Pescados', 'https://cdn-icons-png.flaticon.com/128/1046/1046747.png', 24, 0),
    (25, None, 'Mariscos', 'https://cdn-icons-png.flaticon.com/128/2252/2252076.png', 25, 0),
    (26, None, 'Cerdo', 'https://cdn-icons-png.flaticon.com/128/2674/2674486.png', 26, 0),
    (27, None, 'Costillas', 'https://cdn-icons-png.flaticon.com/128/1046/1046775.png', 27, 0),
    (28, None, 'BBQ', 'https://cdn-icons-png.flaticon.com/128/3480/3480636.png', 28, 0),
    (29, None, 'Sopas', 'https://cdn-icons-png.flaticon.com/128/2276/2276900.png', 29, 0),
    (30, None, 'Ensaladas', '/static/uploads/categorias/cat_d6ae2678.png', 5, 1),
    (31, None, 'Arroces', 'https://cdn-icons-png.flaticon.com/128/3480/3480458.png', 31, 0),
    (32, None, 'Platos del Día', 'https://cdn-icons-png.flaticon.com/128/2921/2921795.png', 32, 0),
    (33, None, 'Desayunos', '/static/uploads/categorias/cat_e100a26e.png', 7, 1),
    (34, None, 'Brunch', 'https://cdn-icons-png.flaticon.com/128/3480/3480540.png', 34, 0),
    (35, None, 'Entradas', 'https://cdn-icons-png.flaticon.com/128/2515/2515183.png', 35, 0),
    (36, None, 'Acompañamientos', 'https://cdn-icons-png.flaticon.com/128/3480/3480599.png', 36, 0),
    (37, None, 'Postres', '/static/uploads/categorias/cat_d254666d.png', 18, 0),
    (38, None, 'Helados', 'https://cdn-icons-png.flaticon.com/128/938/938063.png', 38, 0),
    (39, None, 'Pasteles', 'https://cdn-icons-png.flaticon.com/128/3081/3081949.png', 39, 0),
    (40, None, 'Brownies', 'https://cdn-icons-png.flaticon.com/128/3081/3081898.png', 40, 0),
    (41, None, 'Churros', 'https://cdn-icons-png.flaticon.com/128/3480/3480523.png', 41, 0),
    (42, None, 'Waffles', 'https://cdn-icons-png.flaticon.com/128/3480/3480540.png', 42, 0),
    (43, None, 'Pancakes', 'https://cdn-icons-png.flaticon.com/128/3480/3480531.png', 43, 0),
    (44, None, 'Donuts', 'https://cdn-icons-png.flaticon.com/128/3081/3081880.png', 44, 0),
    (45, None, 'Frutas', 'https://cdn-icons-png.flaticon.com/128/2515/2515280.png', 45, 0),
    (46, None, 'Bebidas', 'https://cdn-icons-png.flaticon.com/128/2738/2738730.png', 46, 0),
    (47, None, 'Jugos', '/static/uploads/categorias/cat_bdce9c2d.png', 11, 1),
    (48, None, 'Smoothies', 'https://cdn-icons-png.flaticon.com/128/2738/2738740.png', 48, 0),
    (49, None, 'Café', '/static/categorias/cafe.png', 19, 1),
    (50, None, 'Té', 'https://cdn-icons-png.flaticon.com/128/2738/2738798.png', 50, 0),
    (51, None, 'Refrescos', 'https://cdn-icons-png.flaticon.com/128/3050/3050094.png', 51, 0),
    (52, None, 'Malteadas', 'https://cdn-icons-png.flaticon.com/128/2738/2738762.png', 52, 0),
    (53, None, 'Aguas Frescas', 'https://cdn-icons-png.flaticon.com/128/2738/2738773.png', 53, 0),
    (54, None, 'Cocteles', 'https://cdn-icons-png.flaticon.com/128/920/920579.png', 54, 0),
    (55, None, 'Cervezas', '/static/uploads/categorias/cat_0ffff7c2.png', 21, 1),
    (56, None, 'Vinos', 'https://cdn-icons-png.flaticon.com/128/920/920566.png', 56, 0),
    (57, None, 'Vegano', 'https://cdn-icons-png.flaticon.com/128/2515/2515263.png', 57, 0),
    (58, None, 'Vegetariano', 'https://cdn-icons-png.flaticon.com/128/2515/2515268.png', 58, 0),
    (59, None, 'Sin Gluten', 'https://cdn-icons-png.flaticon.com/128/3480/3480473.png', 59, 0),
    (60, None, 'Saludable', 'https://cdn-icons-png.flaticon.com/128/2515/2515280.png', 60, 0),
    (61, None, 'Kids', 'https://cdn-icons-png.flaticon.com/128/3081/3081880.png', 61, 0),
    (62, None, 'Combos', 'https://cdn-icons-png.flaticon.com/128/3081/3081840.png', 62, 0),
    (63, None, 'Ofertas', 'https://cdn-icons-png.flaticon.com/128/3081/3081886.png', 63, 0),
    (64, None, 'Populares', 'https://cdn-icons-png.flaticon.com/128/1828/1828884.png', 64, 0),
    (65, None, 'Salchipapas', '/static/categorias/salchipapas.png', 2, 1),
    (66, None, 'Pizzas', '/static/categorias/pizzas.png', 3, 1),
    (67, None, 'Arepas', '/static/uploads/categorias/cat_cbfbe5d7.png', 6, 1),
    (68, None, 'Sanduches', '/static/categorias/sanduches.png', 8, 1),
    (69, None, 'Perros Calientes', '/static/categorias/perros_calientes.png', 9, 1),
    (70, None, 'Pinchos', '/static/uploads/categorias/cat_bb3417eb.png', 10, 1),
    (71, None, 'Gaseosas', '/static/uploads/categorias/cat_cbb51386.png', 12, 1),
    (72, None, 'Asados', '/static/categorias/asados.png', 13, 0),
    (73, None, 'Comida Mexicana', '/static/categorias/comida_mexicana.png', 14, 0),
    (74, None, 'Arabe', '/static/categorias/arabe.png', 15, 0),
    (75, None, 'Asiatica', '/static/categorias/asiatica.png', 16, 0),
    (76, None, 'Panes', '/static/uploads/categorias/cat_368b6bd7.png', 20, 1),
    (77, None, 'Micheladas', '/static/uploads/categorias/cat_0f294782.png', 100, 1),
    (78, None, 'Granizados', '/static/uploads/categorias/cat_2b94335a.png', 101, 1),
    (79, None, 'Jeringas', '/static/uploads/categorias/cat_7ff53a1b.png', 102, 1),
    (80, None, 'Parche Shop', '/static/uploads/categorias/cat_1a441703.png', 103, 1),
    (81, None, 'Mazorcas', '/static/uploads/categorias/cat_7c8fdde4.png', 100, 1),
    (82, None, 'Chuzos Desgranados', '/static/uploads/categorias/cat_c012a7d7.png', 101, 1),
    (83, None, 'Adicionales', '/static/uploads/categorias/cat_bb3441bd.png', 102, 1),
]

for cat in categorias:
    cursor.execute('''
        INSERT INTO categorias_maestras (id, padre_id, nombre, icono_url, orden, activo)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', cat)

conn.commit()
print(f'Importadas {len(categorias)} categorias maestras')
conn.close()
