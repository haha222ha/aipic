async function apiGet(url) {
    try {
        const response = await fetch(url, {
            method: 'GET',
            credentials: 'include',
            headers: { 'Accept': 'application/json' },
        });
        return await response.json();
    } catch (e) {
        console.error('API GET error:', url, e);
        return { code: 500, msg: '网络请求失败', data: null };
    }
}

async function apiPost(url, data) {
    try {
        const response = await fetch(url, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify(data),
        });
        return await response.json();
    } catch (e) {
        console.error('API POST error:', url, e);
        return { code: 500, msg: '网络请求失败', data: null };
    }
}

async function apiDelete(url) {
    try {
        const response = await fetch(url, {
            method: 'DELETE',
            credentials: 'include',
            headers: { 'Accept': 'application/json' },
        });
        return await response.json();
    } catch (e) {
        console.error('API DELETE error:', url, e);
        return { code: 500, msg: '网络请求失败', data: null };
    }
}

async function apiUpload(url, formData) {
    try {
        const response = await fetch(url, {
            method: 'POST',
            credentials: 'include',
            body: formData,
        });
        return await response.json();
    } catch (e) {
        console.error('API UPLOAD error:', url, e);
        return { code: 500, msg: '网络请求失败', data: null };
    }
}
