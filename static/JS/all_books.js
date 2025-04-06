document.getElementById('logoutButton').addEventListener('click', function () {
    localStorage.removeItem('token'); 
    window.location.href = '/logout';  
});
const { createApp } = Vue;
createApp({
data() {
    return {
        currentUser: '',
        sections: [],
        searchQuery: ''
    };
},
methods: {
    fetchCurrentUser() {
    const token = localStorage.getItem('token');
    const headers = { 'Authorization': `Bearer ${token}` };

    axios.get('/api/current_user', { headers })
        .then(response => {
            this.currentUser = response.data;
            console.log(this.currentUser)
        })
        .catch(error => {
            console.error('Error fetching current user:', error);
        });
    },
    fetchBooks() {
        const token = localStorage.getItem('token');
        const headers = { 'Authorization': `Bearer ${token}` };
        axios.get('/api/books_by_section', { headers })
            .then(response => {
                this.sections = response.data;
                console.log(this.sections);
            })
            .catch(error => {
                console.error('Error fetching books:', error);
            });
    },
    handleBookAction(book) {
        const token = localStorage.getItem('token');
        const headers = { 'Authorization': `Bearer ${token}` };
        if (book.status === 'Request') {
            axios.post(`/api/request_book/${book.book_id}`, {}, { headers })
                .then(response => {
                    alert('Request successful');
                    this.fetchBooks();
                })
                .catch(error => {
                    alert(error.response.data.message);
                    // alert(error.message)
                });
        } else {
            window.location.href = `/book_details?bookId=${book.book_id}`;
        }
    },
},
mounted() {
    this.fetchBooks();
    this.fetchCurrentUser();
},
computed: {
    filteredSections() {
        const query = this.searchQuery.toLowerCase();
        return this.sections.map(section => {
            const sectionMatches = section.section_name.toLowerCase().includes(query);
            // Including all books within that section if matches
            if (sectionMatches) {
                return section;
            }
            // Otherwise, filter books within each section based on the search query
            const filteredBooks = section.books.filter(book =>
                book.authors.toLowerCase().includes(query)
            );
            // Including the section only if it has matching books
            if (filteredBooks.length > 0) {
                return {
                    ...section,
                    books: filteredBooks
                };
            }
        }).filter(section => section !== undefined); // Filtering out any undefined sections
    }
},
}).mount('#app3');