from flask_restful import Resource,reqparse
from model import *
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import jsonify ,request
from datetime import datetime, timedelta
from intances import cache

class CurrentUser(Resource):
    @jwt_required()
    def get(self):
        curremail = get_jwt_identity()
        user = User.query.filter_by(email=curremail).first()
        if user:
            return {
                    'username': user.username,        
            }
        return {'message': 'User not found'},404

################################ LIBRARIAN APIS #############################

class SectionResource(Resource):
    @jwt_required()
    def get(self):
        sections = Section.query.all()
        section_list = [
            {
                "id": section.id,
                "name": section.name,
                "description": section.description,
                "date_created": section.date_created.isoformat(),
            } for section in sections
        ]
        return {"sections": section_list}, 200
        
    @jwt_required()
    def post(self):
        section_args = reqparse.RequestParser()
        section_args.add_argument('name', type=str, required=True, help="Name of the section is required")
        section_args.add_argument('description', type=str, required=False)
        args = section_args.parse_args()
        
        new_section = Section(name=args['name'], description=args.get('description'))
        db.session.add(new_section)
        db.session.commit()
        
        return {"message": "Section created", "section_id": new_section.id}, 201

    @jwt_required()
    def put(self, section_id):
        section_args = reqparse.RequestParser()
        section_args.add_argument('name', type=str, required=True, help="Name of the section is required")
        section_args.add_argument('description', type=str, required=False)
        args = section_args.parse_args()
        section = Section.query.get(section_id)
        if not section:
            return {"message": "Section not found"}, 404

        section.name = args['name']
        section.description = args.get('description')
        db.session.commit()
        return {"message": "Section updated"}

    @jwt_required()
    def delete(self, section_id):
        section = Section.query.get(section_id)
        if not section:
            return {"message": "Section not found"}, 404
        db.session.delete(section)
        db.session.commit()
        return {"message": "Section deleted"}, 200

class BookResource(Resource):
    @jwt_required()
    def get(self, section_id):
        books = Book.query.filter_by(section_id=section_id).all()
        if not books:
            return {"message": "No books found in this section"}, 404

        book_list = [
            {
                "id": book.id,
                "title": book.title,
                "content": book.content,
                "authors": book.authors,
                "rating": book.rating
            } for book in books
        ]

        return {"books": book_list}, 200
        

    @jwt_required()
    def post(self, section_id):
        book_args = reqparse.RequestParser()
        book_args.add_argument('title', type=str, required=True, help="Title of the book is required")
        book_args.add_argument('content', type=str, required=True, help="Content of the book is required")
        book_args.add_argument('authors', type=str, required=True, help="Authors of the book are required")
        book_args.add_argument('rating', type=float, required=False, help="Rating of the book is optional")

        args = book_args.parse_args()
        print("Received book arguments:", args)

        section = Section.query.get(section_id)
        if not section:
            return {"message": "Section not found"}, 404

        if not args['title'] or not args['content'] or not args['authors']:
            return {"message": "Missing required fields"}, 400
        
        if args['rating'] is not None and not isinstance(args['rating'], float):
            return {"message": "Rating must be a float"}, 400

        new_book = Book(
            title=args['title'],
            content=args['content'],
            authors=args['authors'],
            rating=args.get('rating'),
            section_id=section_id
        )

        print("New book to add:", new_book)
        db.session.add(new_book)
        db.session.commit()

        return {"message": "Book added successfully", "book_id": new_book.id}, 201
    
    @jwt_required()
    def put(self, section_id, book_id):
        book = Book.query.filter_by(id=book_id, section_id=section_id).first()
        if not book:
            return {"message": "Book not found"}, 404

        data = request.get_json()
        book.title = data.get('title', book.title)
        book.authors = data.get('authors', book.authors)
        book.content = data.get('content', book.content)
        book.rating = data.get('rating', book.rating)

        db.session.commit()
        return jsonify({"message": "Book updated", "book": {
            "id": book.id,
            "title": book.title,
            "authors": book.authors,
            "content": book.content,
            "rating": book.rating
        }})

    @jwt_required()
    def delete(self, section_id, book_id):
        book = Book.query.filter_by(id=book_id, section_id=section_id).first()
        if not book:
            return {"message": "Book not found"}, 404
        
        BookStatus.query.filter_by(book_id=book_id).delete(synchronize_session=False)
        BookIssued.query.filter_by(book_id=book_id).delete(synchronize_session=False)

        db.session.delete(book)
        db.session.commit()
        return {"message": "Book deleted"}

class AllBooksResource(Resource):
    @jwt_required()
    @cache.cached(timeout=50)
    def get(self):
        books = Book.query.join(Section).add_columns(
            Book.id,
            Book.title,
            Book.content,
            Book.authors,
            Book.rating,
            Section.name.label('section_name'),  
            Section.description.label('section_description')
        ).all()

        book_list = [
            {
                "id": book.id,
                "title": book.title,
                "content": book.content,
                "authors": book.authors,
                "rating": book.rating,
                "section": {
                    "name": book.section_name,
                    "description": book.section_description  
                }
            } for book in books
        ]

        return {"books": book_list}, 200

class RequestedBooksResource(Resource):
    @jwt_required()
    def get(self):
        requested_books = db.session.query(
            BookStatus.id,
            BookStatus.book_id,
            BookStatus.user_id,
            Book.title
        ).join(Book, BookStatus.book_id == Book.id).filter(BookStatus.is_requested == 1, BookStatus.is_allocated == 0).all()

        requested_books_list = [
            {
                "id": book.id,
                "book_id": book.book_id,
                "user_id": book.user_id,
                "title": book.title  
            } for book in requested_books
        ]
        return {"requested_books": requested_books_list}, 200

       
class GrantBookResource(Resource):
    @jwt_required()
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('book_id', type=int, required=True, help="Book ID is required")
        parser.add_argument('user_id', type=str, required=True, help="User ID is required")
        args = parser.parse_args()

        book_status = BookStatus.query.filter_by(user_id=args['user_id'],book_id=args['book_id'], is_requested=1, is_allocated=0).first()
        if book_status:
            book_status.is_allocated = 1
            book_status.is_requested = 0
            book_status.date_of_issue = datetime.now()
            book_status.return_date = datetime.now() + timedelta(days=7)  # Assume a 7-day loan period
            db.session.commit()

            user_book = BookIssued.query.filter_by(user_id=args['user_id'], book_id=args['book_id']).first()
            if user_book:
                    user_book.date_of_issue = datetime.now()
                    user_book.return_date = datetime.now() + timedelta(days=7)
                    user_book.returned = 0
            else:
                user_book = BookIssued(user_id=args['user_id'], book_id=args['book_id'], date_of_issue=datetime.now(), return_date=datetime.now() + timedelta(days=7), returned=0)
                db.session.add(user_book)
            db.session.commit()
            return {'message': 'Book granted successfully'}, 200
        return {'message': 'Book not found or already allocated'}, 404

class RejectBookResource(Resource):
    @jwt_required()
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('book_id', type=int, required=True, help="Book ID is required")
        parser.add_argument('user_id', type=str, required=True, help="Book ID is required")
        args = parser.parse_args()

        book_status = BookStatus.query.filter_by(user_id=args['user_id'],book_id=args['book_id'], is_requested=1, is_allocated=0).first()
        if book_status:
            book_status.is_requested = 0  # Setting is_requested to 0 to indicate rejection
            db.session.commit()
            return {'message': 'Book request rejected successfully'}, 200
        return {'message': 'Book not found or not eligible for rejection'}, 404

class AllocatedBooksResource(Resource):
    @jwt_required()
    def get(self):
        alloc_books = db.session.query(
            BookStatus.id,
            BookStatus.book_id,
            BookStatus.user_id,
            BookStatus.date_of_issue,
            BookStatus.return_date,
            Book.title
        ).join(Book, BookStatus.book_id == Book.id).filter(BookStatus.is_allocated == 1).all()

        allocated_books_list = [
            {
                'aid': book.id, 
                'book_id': book.book_id,
                'user_id': book.user_id,
                'title': book.title,  
                'date_of_issue': book.date_of_issue.strftime('%Y-%m-%d %H:%M:%S') if book.date_of_issue else None,
                'return_date': book.return_date.strftime('%Y-%m-%d %H:%M:%S') if book.return_date else None
            } for book in alloc_books
        ]
        return {"allocated_books": allocated_books_list}, 200
   
class RevokeAccessResource(Resource):
    @jwt_required()
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('a_id', type=int, required=True, help="Allocation ID is required")
        parser.add_argument('book_id', type=int, required=True, help="Book ID is required")
        parser.add_argument('user_id', type=str, required=True, help="User ID is required")
        args = parser.parse_args()

        x = BookIssued.query.filter_by(book_id=args['book_id'],user_id=args['user_id'],returned= 0).first()
        if x:
            x.returned =1
            db.session.commit()
            book_status = BookStatus.query.filter_by(id=args['a_id']).first()
            if book_status:
                book_status.is_allocated =0
                book_status.is_requested =0
                book_status.date_of_issue = None
                book_status.return_date =None

                db.session.commit()
            else:
                return {"error": "BookStatus record not found"}, 404
        else:
            return {"error": "User book record not found"}, 404
        return {"message": "Book revoked successfully"}, 200


################################### USER APIS #################################

class BooksBySection(Resource):
    @jwt_required()
    def get(self):
        curr_user_id = get_jwt_identity() 
        sections = Section.query.all()
        result = []
        for section in sections:
            books = Book.query.filter_by(section_id=section.id).all()
            books_data = []

            for book in books:
                existing_book_status = BookStatus.query.filter_by(book_id=book.id, user_id=curr_user_id).first()
                
                if not existing_book_status:
                    new_book = BookStatus(
                    book_id=book.id,
                    user_id=curr_user_id,
                    is_allocated=0,
                    is_requested=0
                    )
                    db.session.add(new_book)
                db.session.commit() 
            
            for book in books:
                book_status = BookStatus.query.filter_by(book_id=book.id,user_id=curr_user_id).first()
                if book_status.is_allocated:
                    status = 'Allocated'
                elif book_status.is_requested and not book_status.is_allocated:
                    status = 'Requested'
                else:
                    status = 'Request'
                books_data.append({
                    'book_id': book.id,
                    'title': book.title,
                    'authors': book.authors, 
                    'rating': book.rating,
                    'status': status
                })
            result.append({
                'section_name': section.name,
                'books': books_data
            })
        return result, 200

class RequestBook(Resource):
    @jwt_required()
    def post(self, book_id):
        curr_user_id = get_jwt_identity()  # as user ID is stored in JWT identity
        book_status = BookStatus.query.filter_by(book_id=book_id,user_id=curr_user_id).first()

        # Check if the book is already requested or allocated
        if book_status and (book_status.is_requested or book_status.is_allocated):
            return {'message': 'Book is already requested or allocated'}, 400
        
    
        nallocated_books = BookStatus.query.filter_by(user_id=curr_user_id, is_allocated=1).count()
        nrequested_books = BookStatus.query.filter_by(user_id=curr_user_id, is_requested=1).count()
        if nallocated_books + nrequested_books >= 5:
            return {'message': 'Not more than 5 books can be requested by a user at a time'}, 400

        # If no existing status, create a new entry
        if not book_status:
            book_status = BookStatus(book_id=book_id, user_id=curr_user_id, is_requested=1, is_allocated=0)
            db.session.add(book_status)
        else:
            book_status.is_requested = 1
            book_status.user_id = curr_user_id
        
        db.session.commit()
        return {'message': 'Book request submitted successfully'}, 200

class BookDetails(Resource):
    @jwt_required()
    def get(self, book_id):
        book = Book.query.get(book_id)
        if not book:
            return {'message': 'Book not found'}, 404
        book_status = BookStatus.query.filter_by(book_id=book_id).first()
        
        if book_status.is_allocated:
            status = 'Allocated'
        elif book_status.is_requested and not book_status.is_allocated:
            status = 'Requested'
        else:
            status = 'Request'
        return {
            'id': book.id,
            'title': book.title,
            'content': book.content,
            'authors': book.authors,
            'rating': book.rating,
            # 'status': 'Allocated' if book_status and book_status.is_allocated else 'Request'
            'status': status
        }, 200

class ReturnBook(Resource):
    @jwt_required()
    def post(self, book_id):
        curr_user_id = get_jwt_identity() 
        book_status = BookStatus.query.filter_by(book_id=book_id, user_id=curr_user_id, is_allocated=1).first()
        if book_status:
            book_status.is_allocated = 0  
            book_status.date_of_issue= None
            book_status.return_date= None
                
            db.session.commit()
            
            user_book = BookIssued.query.filter_by(book_id=book_id, user_id=curr_user_id, returned=0).first()
            if user_book:
                user_book.returned = 1
                db.session.commit()
                return {'message': 'Book returned successfully'}, 200
            return {'message': 'Book status updated, no book issued record updated'}, 200
        return {'message': 'Invalid request or book not found'}, 400

class FeedBack(Resource):
    @jwt_required()
    def post(self):
        curr_user_id =  get_jwt_identity()
        parser = reqparse.RequestParser()
        parser.add_argument('book_id', type=int, required=True, help="Book ID is required")
        parser.add_argument('rating', type=int, required=True, help="Rating is required")
        parser.add_argument('feedback', type=str, required=True, help="Feedback is required")
        args = parser.parse_args()
        
        print(f'Received feedback: User ID: {curr_user_id}, Book ID: {args["book_id"]}, Rating: {args["rating"]}, Feedback: {args["feedback"]}')


        if not curr_user_id or not args['book_id'] or not args['rating'] or not args['feedback']:
            return {'message': 'Missing data'}, 400

        issued_book = BookIssued.query.filter_by(user_id=curr_user_id, book_id=args['book_id']).first()
        if issued_book:
            print(f'Received')

        if not issued_book:
            return {'message': 'Issued book record not found'}, 404
        
        
        issued_book.rating = args['rating']
        issued_book.feedback = args['feedback']

        db.session.commit()

        return {'message': 'Feedback submitted successfully!'}, 200

class ReturnedBooks(Resource):
    @jwt_required()
    def get(self):
        curr_user_id = get_jwt_identity()
        results = db.session.query(
            Book.title.label('title'),
            BookIssued.date_of_issue,
            BookIssued.return_date,
            BookIssued.rating,
            BookIssued.feedback
        ).join(Book, BookIssued.book_id == Book.id).filter(BookIssued.user_id == curr_user_id, BookIssued.returned == 1).all()


        returned_books = [{
            'book_title': r.title,
            'date_of_issue': r.date_of_issue.isoformat(),
            'return_date': r.return_date.isoformat(),
            'rating': r.rating,
            'feedback': r.feedback,
        } for r in results]

        return {'returned_books': returned_books},200

class IssuedBooks(Resource):
    @jwt_required()
    def get(self):
        curr_user_id = get_jwt_identity()

        # select_from is used to explicitly specify the starting point of the query
        issued_books = db.session.query(
            BookStatus.book_id,
            Book.title.label('book_title'),
            Section.name.label('section_name'),
            BookStatus.date_of_issue,
            BookStatus.return_date
        ).select_from(BookStatus).join(
            Book, BookStatus.book_id == Book.id
            ).join( Section, Book.section_id == Section.id).filter(BookStatus.user_id == curr_user_id,BookStatus.is_allocated == 1).all()

        issued_books_list = [{
            'book_id': r.book_id,
            'section': r.section_name,
            'book_title': r.book_title,
            'date_of_issue': r.date_of_issue.isoformat(),
            'return_date': r.return_date.isoformat(),
        } for r in issued_books]

        return {'issued_books': issued_books_list}, 200
  
################################## STATS APIS ##################################

class LibStatistics(Resource):
    @jwt_required()
    def get(self):
        # Fetch section data
        sections = Section.query.all()
        section_data = [{
            'section_name': section.name,
            'books_count': len(section.books)
        } for section in sections]


        allocated_books_list = []
        for section in sections:
            allocated_count = db.session.query(BookStatus).join(Book).filter(
                Book.section_id == section.id,
                BookStatus.is_allocated == 1
            ).count()
            allocated_books_list.append({
                'section_name': section.name,
                'books_allocated': allocated_count
            })

        data = {
            'sections': section_data,
            'allocated_books': allocated_books_list  
        }

        return {'data': data},200
    
class UsrStatistics(Resource):
    @jwt_required()
    def get(self):
        curr_user_id = get_jwt_identity() 

        sections = Section.query.all()
        data = []
        for section in sections:
            # Count read books in section
            read_count = db.session.query(BookIssued).join(Book).filter(
                Book.section_id == section.id,
                BookIssued.user_id == curr_user_id
            ).count()

            # Count issued books in section
            alloc_count = db.session.query(BookStatus).join(Book).filter(
                Book.section_id == section.id,
                BookStatus.is_allocated == 1,
                BookStatus.user_id == curr_user_id
            ).count()

            # Count returned books in section
            returned_count = db.session.query(BookIssued).join(Book).filter(
                Book.section_id == section.id,
                BookIssued.returned == 1,
                BookIssued.user_id == curr_user_id
            ).count()

            data.append({
                'section_name': section.name,
                'books_read': read_count,
                'books_allocated': alloc_count,
                'books_returned': returned_count
            })

        return {'data': data}, 200

