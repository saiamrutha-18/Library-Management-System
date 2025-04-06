document.getElementById('logoutButton').addEventListener('click', function () {
    localStorage.removeItem('token'); 
    window.location.href = '/logout';  
});
const app = Vue.createApp({
data() {
    return {
        currentUser: '',
        sections: [],
        sectionId:null,
        flag: 0,
        newSection: {
            name: '',
            description: '',
           
        },
        searchBar: "",
        taskId: null,
        isProcessing: false
    };
},
mounted() {
    this.fetchCurrentUser();
    this.fetchSections();
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

    fetchSections() {
        const token = localStorage.getItem('token');
        const headers = {
            'Authorization': `Bearer ${token}`
        };
        axios.get('/api/sections',{ headers })
            .then(response => {
                this.sections = response.data.sections;
                console.log(this.sections)
            })
            .catch(error => {
                console.error('Error fetching sections:', error);
            });
    },
    
    addSection() {
        const token = localStorage.getItem('token');
        const headers = {
            'Authorization': `Bearer ${token}`
        };

        axios.post('/api/sections', this.newSection, { headers })
            .then(response => {
                console.log('Section added successfully:', response.data.sections);
                this.fetchSections();
                this.newSection.name = '';
                this.newSection.description = '';
                
            })
            .catch(error => {
                console.error('Error adding section:', error);
                alert('Error adding section');
            });
    },

    deleteSection(sectionId) {
        const token = localStorage.getItem('token');
        const headers = {
            'Authorization': `Bearer ${token}`
        };

        axios.delete(`/api/sections/${sectionId}`, { headers })
            .then(response => {
                console.log('Section deleted successfully:', response.data);
                this.fetchSections();
            })
            .catch(error => {
                console.error('Error deleting section:', error);
                alert('Error deleting section');
            });
    },

    startUpdateSec(section) {
        this.newSection = { ...section }; 
        this.sectionId=section.id;
        this.flag=1;
       
    },
   
    updateSection(sectionId) {
        const token = localStorage.getItem('token');
        const headers = {
            'Authorization': `Bearer ${token}`
        };

        axios.put(`/api/sections/${sectionId}`,this.newSection, { headers })
            .then(response => {
                console.log('Section updated successfully:', response.data);
                this.fetchSections();
                this.flag=0;
                this.newSection.name = '';
                this.newSection.description = '';
            })
            .catch(error => {
                console.error('Error updating section:', error);
                alert('Error updating section');
            });
    },

    navigateToAddBook(sectionId) {
        window.location.href = `/add_book?sectionId=${sectionId}`;
    },


    async  triggerAndPollExport() {
        try {
                
                const token = localStorage.getItem('token');
                const headers = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };
                const response = await axios.post('/triger_celery_job', { email: 'admin@example.com' }, { headers });
                this.taskId = response.data.Task_ID;

                // Poll for task completion
                const pollInterval = setInterval(async () => {
                    try {
                        const statusResponse = await axios.get(`/status/${this.taskId}`, { headers });
                        const data = statusResponse.data;

                        if (data.Task_State === "SUCCESS") {
                            clearInterval(pollInterval);
                            window.location.href = '/download-csv';  
                        }
                    } catch (statusError) {
                        console.error("Error polling for completion:", statusError);
                    }
                }, 5000); 

            } catch (error) {
                console.error("Error triggering export:", error);
            }
    }


},
computed: {
    searchSections() {
    return this.sections.filter(section =>
        section.name.toLowerCase().includes(this.searchBar.toLowerCase())
    );
    },
   
    buttonLabel() {
        return this.flag == 1 ? 'Save Section' : 'Add Section';
    }
},

});

app.mount('#app');