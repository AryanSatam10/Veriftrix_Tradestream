import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export const uploadInvoice = async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await axios.post(`${API_BASE_URL}/upload-lc`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
                'Accept': 'application/json'
            }
        });
        return response.data;
    } catch (error) {
        console.error("API Error:", error);
        throw new Error(error.response?.data?.detail || 'Failed to process document');
    }
};

// Handle the human-in-the-loop decision with a real backend PUT request
export const updateTransactionStatus = async (transactionId, decision) => {
    try {
        const response = await axios.put(`${API_BASE_URL}/transactions/${transactionId}/status`, {
            status: decision === 'CLEARED' ? 'CLEARED' : 'REJECTED'
        });
        return response.data;
    } catch (error) {
        console.error("Failed to push human decision state to gateway:", error);
        throw new Error(error.response?.data?.detail || 'Failed to update transaction status');
    }
};

// Fetch live dashboard analytics from the persistent backend cache
export const fetchAnalytics = async () => {
    try {
        const response = await axios.get(`${API_BASE_URL}/analytics`);
        return response.data;
    } catch (error) {
        console.error("Failed to fetch real analytics:", error);
        return { kpis: { total_volume: 0, processed_count: 0, intervention_rate: 0 }, chart_data: [], recent_transactions: [] };
    }
};