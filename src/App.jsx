import { useState } from "react";
import axios from "axios";
import './App.css';

function App() {
  const [image, setImage] = useState(null);
  const [generatedShares, setGeneratedShares] = useState([]);
  const [fetchedShares, setFetchedShares] = useState([]);
  const [decryptedImage, setDecryptedImage] = useState(null);
  const [loadingEncrypt, setLoadingEncrypt] = useState(false);
  const [loadingUpload, setLoadingUpload] = useState(false);
  const [loadingFetch, setLoadingFetch] = useState(false);
  const [loadingDecrypt, setLoadingDecrypt] = useState(false);

  const handleImageUpload = (event) => {
    setImage(event.target.files[0]);
    setGeneratedShares([]); // Clear previous shares when uploading a new image
    setFetchedShares([]);   // Clear fetched shares
    setDecryptedImage(null); // Clear decrypted image
  };

  const applyEVCT = async () => {
    if (!image) {
      alert("Please select an image first.");
      return;
    }
    const formData = new FormData();
    formData.append("image", image);

    setLoadingEncrypt(true);
    try {
      // const response = await axios.post("http://localhost:5000/encrypt", formData);
      const response = await axios.post("https://flask-backend-i46p.onrender.com/encrypt", formData);
      setGeneratedShares(response.data.shares);
      setFetchedShares([]); // clear previous fetch result
      setDecryptedImage(null); // clear previous decryption
    } catch (error) {
      console.error("Error applying 3,3 EVCT:", error);
    } finally {
      setLoadingEncrypt(false);
    }
  };

  const encryptAndUpload = async () => {
    setDecryptedImage(null);
    if (!generatedShares.length) {
      alert("Generate shares first!");
      return;
    }
    setLoadingUpload(true);
    try {
      // await axios.post("http://localhost:5000/upload", { shares: generatedShares });
      await axios.post("https://flask-backend-i46p.onrender.com/upload", { shares: generatedShares });
      alert("Shares were successfully encrypted and uploaded to the cloud");
      setFetchedShares([]);
      setDecryptedImage(null);
    } catch (error) {
      console.error("Upload failed:", error);
    } finally {
      setLoadingUpload(false);
    }
  };

  const fetchAndDecryptToShares = async () => {
    if (generatedShares.length === 0) {
      alert("Please generate shares first.");
      return;
    }
  
    let attempts = 0;
    while (attempts < 3) {
      const userKey = prompt("Enter AES Key (16 characters):");
  
      if (userKey === null) {
        alert("Operation cancelled.");
        return;  // Exit if the user cancels
      }
  
      if (userKey.length !== 16) {
        alert("Key must be exactly 16 characters.");
        continue;  // Ask the user again if the key is not 16 characters
      }
  
      setLoadingFetch(true);
      try {
        // const response = await axios.post("http://localhost:5000/fetch", {
        const response = await axios.post("https://flask-backend-i46p.onrender.com/fetch", {
          num_shares: generatedShares.length,
          aes_key: userKey,
        });
  
        // If the server sends shares, show them
        if (response.data && response.data.shares) {
          setFetchedShares(response.data.shares);
          alert("Shares successfully fetched and decrypted!");
          setDecryptedImage(null);  // Clear any previously decrypted image
          setLoadingFetch(false);
          return;
        }
      } catch (error) {
        attempts++;
        setLoadingFetch(false);
  
        // Handle error response from the backend (401 Unauthorized)
        if (error.response && error.response.status === 401) {
          alert("Incorrect key. Please try again.");
        } else {
          alert(`An error occurred: ${error.message}`);
        }
  
        if (attempts >= 3) {
          alert("Maximum attempts reached.");
          console.error("An error occurred:", error);
          return;
        } else {
          alert(`Incorrect key. Attempts remaining: ${3 - attempts}`);
        }
      }
    }
  };
  

  const decryptImage = async () => {
    if (fetchedShares.length === 0) {
      alert("Please generate shares first.");
      return;
    }
    setLoadingDecrypt(true);
    try {
      // const response = await axios.post("http://localhost:5000/decrypt", {
      const response = await axios.post("https://flask-backend-i46p.onrender.com/decrypt", {
        shares: fetchedShares,
        num_shares: fetchedShares.length
      });
      setDecryptedImage(response.data.decrypted_image);
    } catch (error) {
      console.error("Decryption failed:", error);
    } finally {
      setLoadingDecrypt(false);
    }
  };

  return (
    <div className="cont">
      <h1 style={{justifyContent:'center'}}> VISUAL CRYPTOGRAPHY </h1>
      <div className="cont-1">
        <h2>Select an image :</h2>
        <input style={{marginLeft: '30px', fontSize:'15px', paddingBottom:'5px'}} type="file" onChange={handleImageUpload} />
      </div>
      <div style={{gap:'10px',display:'flex', justifyContent:'center'}}>
        <button onClick={applyEVCT}>Encrypt Image</button>
        <button onClick={encryptAndUpload}>Encrypt and upload to cloud</button>
        <button onClick={fetchAndDecryptToShares}>Fetch from cloud</button>
        <button onClick={decryptImage}>Decrypt Image</button>
      </div>
      <div className="loading">
        {loadingEncrypt && <div className="spinner"></div>}
        {loadingUpload && <div className="spinner"></div>}

        {loadingFetch && <div className="spinner"></div>}
        {loadingDecrypt && <div className="spinner"></div>}
      </div>

      {/* {loadingEncrypt && <div className="spinner"></div>} */}
      {generatedShares.length > 0 && (
        <div className="dim">
          <h3>Shares:</h3>
          <div className="shares">
            {generatedShares.map((share, idx) => (
              <img key={idx} src={`data:image/png;base64,${share}`} alt={`Share ${idx + 1}`} width={200} />
            ))}
          </div>
        </div>
      )}

      {/* {loadingUpload && <div className="spinner"></div>}

      {loadingFetch && <div className="spinner"></div>} */}
      {fetchedShares.length > 0 && (
        <div className="dim">
          <h3>Decrypted Shares:</h3>
          <div className="shares">
            {fetchedShares.map((share, idx) => (
              <img key={idx} src={`data:image/png;base64,${share}`} alt={`Fetched Share ${idx + 1}`} width={200} />
            ))}
          </div>
        </div>
      )}

      {/* {loadingDecrypt && <div className="spinner"></div>} */}
      {decryptedImage && (
        <div className="final">
          <h4>Decrypted Image:</h4>
          <img src={`data:image/png;base64,${decryptedImage}`} alt="Decrypted" width={200} />
        </div>
      )}
    </div>
  );
}

export default App;