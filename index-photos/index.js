
const AWS = require('aws-sdk');
const { Client } = require('@opensearch-project/opensearch');

const rekognition = new AWS.Rekognition();
const s3 = new AWS.S3();

const esClient = new Client({
  node: 'https://search-photos-mm5eyjsilg65lx5qv4qsmnf2rm.aos.us-east-1.on.aws',
  auth: {
    username: 'admin',
    password: 'Admin_123'
  }
});

exports.handler = async (event) => {
  try {
    console.log("Event:", JSON.stringify(event, null, 2));

    const bucket = event.Records[0].s3.bucket.name;
    const objectKey = decodeURIComponent(event.Records[0].s3.object.key.replace(/\+/g, ' '));

    const s3Metadata = await s3.headObject({
      Bucket: bucket,
      Key: objectKey
    }).promise();

    let customLabels = [];
    if (s3Metadata.Metadata && s3Metadata.Metadata['customlabels']) {
      customLabels = s3Metadata.Metadata['customlabels'].split(',').map(label => label.trim().toLowerCase());
    }

    const rekognitionParams = {
      Image: {
        S3Object: {
          Bucket: bucket,
          Name: objectKey
        }
      },
      MaxLabels: 50,
      MinConfidence: 70
    };

    const rekognitionResponse = await rekognition.detectLabels(rekognitionParams).promise();
    const rekognitionLabels = rekognitionResponse.Labels.map(label => label.Name.toLowerCase());

    const allLabels = [...new Set([...rekognitionLabels, ...customLabels])];

    const document = {
      objectKey: objectKey,
      bucket: bucket,
      createdTimestamp: new Date().toISOString(),
      labels: allLabels
    };

    const response = await esClient.index({
      index: 'photos1',
      body: document
    });

    console.log("Indexed successfully:", response);
    return {
      statusCode: 200,
      body: JSON.stringify({ message: 'Indexed successfully' })
    };
  } catch (error) {
    console.error("Error indexing:", error);
    return {
      statusCode: 500,
      body: JSON.stringify({ message: 'Failed to index', error: error.message })
    };
  }
};
