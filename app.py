from flask import Flask, json, redirect, render_template
from flask_mysqldb import MySQL
from flask import request

app = Flask(__name__)

app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.ERROR)

# DATABASE CONNECTION
app.config["MYSQL_HOST"] = "classmysql.engr.oregonstate.edu"
app.config["MYSQL_USER"] = "cs340_caiso"
app.config["MYSQL_PASSWORD"] = "8125"
app.config["MYSQL_DB"] = "cs340_caiso"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)

#********************#
#  HOMEPAGE ENDPOINT #
#********************#
@app.route('/')
def home_page():
    return render_template('homepage.html')

#**********************#
#  CUSTOMERS ENDPOINTS #
#**********************#
@app.route('/Customers', methods=["POST", "GET"])
def customers():
    #--------------------------#
    #  CUSTOMER POST REQUESTS  #
    #--------------------------#
    if request.method == "POST":
        ### ADD A NEW CUSTOMER ###
        if request.form.get("Add_Customer"):
            # Collect new customer inputs
            first_name = request.form["firstName"]
            last_name = request.form["lastName"]
            email = request.form["email"]
            birthday = request.form["birthday"]

            # Insert new customer to table
            customerInsertQuery = "INSERT INTO Customers (first_name, last_name, email, birthday) VALUES(%s, %s, %s, %s)"
            cur = mysql.connection.cursor()
            cur.execute(customerInsertQuery, (first_name, last_name, email, birthday))
            mysql.connection.commit()

            # Refresh page
            return redirect("/Customers")

        ### UPDATE EXISTING CUSTOMER ###
        if request.form.get("Update_Customer"):
            customer_ID = request.form["customer_ID"]
            first_name = request.form["firstName"]
            last_name = request.form["lastName"]
            email = request.form["email"]
            birthday = request.form["birthday"]

            updateCustomerQuery = "UPDATE Customers \
                    SET first_name = IF(%s != '',%s, first_name),\
                        last_name = IF(%s != '',%s, last_name),\
                        email = IF(%s != '',%s, email),\
                        birthday = IF(%s != '',%s, birthday)\
                    WHERE customer_ID = %s"
            cur = mysql.connection.cursor()
            cur.execute(updateCustomerQuery, (first_name,first_name,last_name,last_name,email,email,birthday,birthday,customer_ID))
            mysql.connection.commit()

            return redirect("/Customers")

    #-------------------------#
    #  CUSTOMER GET REQUESTS  #
    #-------------------------#
    ### POPULATE CUSTOMERS TABLE ###
    if request.method == "GET":
        query = 'SELECT * FROM Customers'
        cursor = mysql.connection.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        return render_template('customers.html', rows=results)

#*******************#
#  ORDERS ENDPOINTS #
#*******************#
@app.route('/Orders', methods=["POST", "GET"])
def orders():
    #------------------------#
    #  ORDERS POST REQUESTS  #
    #------------------------#
    if request.method == "POST":
        ### ADD A NEW ORDER ###
        if request.form.get("Add_Order"):
            shop = request.form["orderShop"]
            customer = request.form["orderCustomer"]

            addOrderQuery = "INSERT INTO Orders (drink_quantity, shop, customer, date, price) VALUES(0, %s, %s, DATE(SYSDATE()), 0)"
            cur = mysql.connection.cursor()
            cur.execute(addOrderQuery, (shop, customer))
            mysql.connection.commit()

            return redirect("/Orders")

        ### UPDATE EXISTING ORDER ###
        if request.form.get("Update_Order"):
            order_ID = request.form["order_ID"]
            shop = request.form["shop"]
            customer = request.form["customer"]

            updateOrderQuery = "UPDATE Orders \
                    SET shop = IF(%s != '',%s, shop),\
                        customer = IF(%s != '',%s, customer)\
                    WHERE order_ID = %s"
            cur = mysql.connection.cursor()
            cur.execute(updateOrderQuery, (shop,shop,customer,customer,order_ID))
            mysql.connection.commit()

            return redirect("/Orders")

        ### ADD A NEW ORDER ITEM TO AN EXISTING ORDER ###
        if request.form.get("Add_Order_Item"):
            order_ID = request.form["orderID"]
            tea_type = request.form["orderTeaType"]
            cup_size = request.form["orderCupSize"]
            topping = request.form["orderTopping"]
            quantity = request.form["orderQuantity"]

            # Insert the new Order Item
            query1 = "INSERT INTO Order_Items (order_ID, tea_type, cup_size, topping, quantity, price) VALUES(%s, %s, %s, %s, %s, 0)"
            cur = mysql.connection.cursor()
            cur.execute(query1, (order_ID, tea_type, cup_size, topping, quantity))
            mysql.connection.commit()

            # Update Order Item Price
            query2 = "UPDATE Order_Items\
                        SET price = price + ((SELECT price FROM Materials WHERE material_ID = %s) + \
                                             (SELECT price FROM Materials WHERE material_ID = %s) + \
                                             (SELECT price FROM Materials WHERE material_ID = %s)) * quantity \
                        WHERE item_ID = (SELECT last_insert_id())"
            cur = mysql.connection.cursor()
            cur.execute(query2,(tea_type, cup_size, topping,))
            mysql.connection.commit()

            # Update the quantity and price in the Order Summary
            query3 = "UPDATE Orders \
                        SET price = price + (SELECT price from Order_Items where item_ID = (SELECT last_insert_id())), \
                            drink_quantity = drink_quantity + (SELECT quantity from Order_Items where item_ID = (SELECT last_insert_id())) \
                        WHERE order_ID = %s"
            cur = mysql.connection.cursor()
            cur.execute(query3,(order_ID,))
            mysql.connection.commit()

            # Update the quantities used in the Materials table
            query4 = "Update Materials \
                        SET quantity = quantity - (SELECT quantity FROM Order_Items WHERE item_ID = (SELECT last_insert_id()))\
                        WHERE material_ID = %s"
            cur = mysql.connection.cursor()
            cur.execute(query4,(tea_type,))
            mysql.connection.commit()

            query5 = "Update Materials \
                        SET quantity = quantity - (SELECT quantity FROM Order_Items WHERE item_ID = (SELECT last_insert_id()))\
                        WHERE material_ID = %s"
            cur = mysql.connection.cursor()
            cur.execute(query5,(cup_size,))
            mysql.connection.commit()

            query6 = "Update Materials \
                        SET quantity = quantity - (SELECT quantity FROM Order_Items WHERE item_ID = (SELECT last_insert_id()))\
                        WHERE material_ID = %s"
            cur = mysql.connection.cursor()
            cur.execute(query6,(topping,))
            mysql.connection.commit()

            return redirect("/Orders")

        ### DELETE AN EXISTING ORDER ITEM ###
        if request.form.get("Delete_Order_Item"):
            item_ID = request.form["item_ID"]
            # Update the Orders table by subtracting the price, quantity
            orderUpdateQuery = "UPDATE Orders \
                                    SET drink_quantity = drink_quantity - (SELECT quantity from Order_Items where item_ID = %s),\
                                        price = price - (SELECT price from Order_Items where item_ID = %s) \
                                    WHERE order_ID = (SELECT order_ID from Order_Items where item_ID = %s)"
            cur = mysql.connection.cursor()
            cur.execute(orderUpdateQuery, (item_ID, item_ID, item_ID,))
            mysql.connection.commit()
            # Delete the item from the Order_Items table
            query = "DELETE FROM Order_Items WHERE item_ID = %s"
            cur = mysql.connection.cursor()
            cur.execute(query, (item_ID,))
            mysql.connection.commit()

            return redirect("/Orders")

        ### DELETE AN EXISTING ORDER ###
        if request.form.get("Delete_Order"):
            order_ID = request.form["order_ID"]
            # Add quantities back to the Materials table
            addBackQuantityQuery = "UPDATE Materials \
                                        SET quantity = quantity + (SELECT)"
            # First Delete the Order Items
            orderItemDeleteQuery = "DELETE FROM Order_Items WHERE order_ID = %s"
            cur = mysql.connection.cursor()
            cur.execute(orderItemDeleteQuery, (order_ID,))
            mysql.connection.commit()
            # Delete the order summary from the Order_Items table
            orderDeleteQuery = "DELETE FROM Order WHERE order_ID = %s"
            cur = mysql.connection.cursor()
            cur.execute(orderDeleteQuery, (order_ID,))
            mysql.connection.commit()

            return redirect("/Orders")

    #----------------------#
    #  ORDER GET REQUESTS  #
    #----------------------#
    if request.method == "GET":
        ### POPULATE ORDERS TABLE ###
        getOrdersQuery = 'SELECT * FROM Orders'
        cursor = mysql.connection.cursor()
        cursor.execute(getOrdersQuery)
        results = cursor.fetchall()

        ### POPULATE ORDER_ITEMS TABLE ###
        getOrderItemsQuery = 'SELECT * FROM Order_Items'
        cursor2 = mysql.connection.cursor()
        cursor2.execute(getOrderItemsQuery)
        results2 = cursor2.fetchall()

        return render_template("orders.html", order_rows=results, item_rows=results2)

#******************#
#  SHOPS ENDPOINTS #
#******************#
@app.route('/Shops', methods=["POST", "GET"])
def Shops():
    #-----------------------#
    #  SHOPS POST REQUESTS  #
    #-----------------------#
    if request.method == "POST":
        ### ADD A NEW SHOP LOCATION ###
        if request.form.get("Add_Shop"):
            street_address = request.form["shopAddress"]
            city = request.form["shopCity"]
            state = request.form["shopState"]
            manager = request.form["shopManager"]

            addShopQuery = "INSERT INTO Shops (street_address, city, state, manager) VALUES(%s, %s, %s, %s)"
            cur = mysql.connection.cursor()
            cur.execute(addShopQuery, (street_address, city, state, manager))
            mysql.connection.commit()

            return redirect("/Shops")
        
        ### UPDATE AN EXISTING SHOP ###
        if request.form.get("Update_Shop"):
            shop_ID = request.form["shop_ID"]
            street_address = request.form["address"]
            city = request.form["city"]
            state = request.form["state"]
            manager = request.form["manager"]

            query = "UPDATE Shops \
                    SET street_address = IF(%s != '',%s, street_address),\
                        city = IF(%s != '',%s, city),\
                        state = IF(%s != '',%s, state),\
                        manager = IF(%s != '',%s, manager)\
                    WHERE shop_ID = %s"
            cur = mysql.connection.cursor()
            cur.execute(query, (street_address,street_address,city,city,state,state,manager,manager,shop_ID))
            mysql.connection.commit()

            return redirect("/Shops")

    #---------------------#
    #  SHOP GET REQUESTS  #
    #---------------------#
    if request.method == "GET":
        ### POPULATE SHOPS TABLE ###
        query = 'SELECT * FROM Shops'
        cursor = mysql.connection.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        return render_template('shops.html', rows=results)

#**********************#
#  MATERIALS ENDPOINTS #
#**********************#
@app.route('/Materials', methods=["POST", "GET"])
def materials():
    #--------------------------#
    #  MATERIAL POST REQUESTS  #
    #--------------------------#
    if request.method == "POST":
        ### UPDATE A MATERIAL ###
        if request.form.get("Update_Material"):
            material_ID = request.form["material_ID"]
            cost = request.form["materialCost"]
            price = request.form["materialPrice"]

            query = "UPDATE Materials \
                    SET cost = IF(%s != '',%s, cost),\
                        price = IF(%s != '',%s, price)\
                    WHERE material_ID = %s"
            cur = mysql.connection.cursor()
            cur.execute(query, (cost,cost,price,price,material_ID))
            mysql.connection.commit()

            return redirect("/Materials")

        ### ORDER MORE OF A MATERIAL ###
        if request.form.get("Order_Material"):
            material_ID = request.form["material_ID"]
            quantity = request.form["quantity"]

            query = "UPDATE Materials SET quantity = (quantity + %s) WHERE material_ID = %s"
            cur = mysql.connection.cursor()
            cur.execute(query, (quantity, material_ID))
            mysql.connection.commit()

            return redirect("/Materials")

        # if request.form.get("Filter_Model"):
        #     # grab user form inputs
        #     brand_id = request.form["brandID"]

        #     query = "SELECT * FROM Model WHERE brand_id = %s"
        #     cur = mysql.connection.cursor()
        #     cur.execute(query, (brand_id,))
        #     mysql.connection.commit()

        #     # redirect back to people page
        #     query = 'SELECT * FROM Model WHERE brand_id = %s'
        #     cursor = mysql.connection.cursor()
        #     cursor.execute(query, (brand_id,))
        #     results = cursor.fetchall()
        #     # currently this would only populate the html table based on what is in the db
        #     return render_template('model.html', rows=results)

    #-------------------------#
    #  MATERIAL GET REQUESTS  #
    #-------------------------#
    if request.method == "GET":
        ### POPULATE MATERIALS TABLE ###
        query = 'SELECT * FROM Materials'
        cursor = mysql.connection.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        return render_template('materials.html', rows=results)

# LISTENER SETUP
if __name__ == "__main__":

    app.run(port=3000, debug=True)
